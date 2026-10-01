"""이미지 업스케일링 도구 (내 PC에서 무료로 실행).

사용 예:
  python upscale.py slime.png                       # 자동 판별 후 4배 → slime_x4.png
  python upscale.py slime.png --scale 2 --out big.png
  python upscale.py dot.png --mode pixel --scale 8  # 강제로 도트 방식
  python upscale.py assets/monsters --scale 2       # 폴더 안 이미지 전부

방식:
  auto  : (기본) 이미지를 분석해 도트 그림이면 pixel, 아니면 ai 로 처리.
  ai    : Real-ESRGAN (그래픽카드 사용). 애니풍·일러스트·배경용. 투명 PNG 지원.
  pixel : 도트(픽셀아트)용. 도트 격자를 찾아 픽셀 하나하나를 또렷하게 복원한 뒤 확대.
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

GRID_SCORE_MIN = 12      # 이 이상이면 일정한 도트 격자가 있다고 판단
SMALL_PIXEL_MAX = 256    # 이 크기 이하 + 색 수가 적으면 원본 해상도 도트로 판단
SMALL_PIXEL_COLORS = 256

HERE = Path(__file__).resolve().parent
ESRGAN = HERE / "realesrgan" / "realesrgan-ncnn-vulkan.exe"
AI_MODELS = {
    "anime": "realesrgan-x4plus-anime",  # 애니풍·게임 일러스트 (기본)
    "photo": "realesrgan-x4plus",        # 실사풍
}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def upscale_ai(src: Path, dst: Path, scale: float, model: str):
    if not ESRGAN.exists():
        sys.exit(f"[오류] Real-ESRGAN이 없습니다: {ESRGAN}")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_in = Path(tmp) / "in.png"
        tmp_out = Path(tmp) / "out.png"
        Image.open(src).save(tmp_in)  # 경로에 한글이 있어도 안전하게 임시 파일로 처리
        result = subprocess.run(
            [str(ESRGAN), "-i", str(tmp_in), "-o", str(tmp_out), "-n", AI_MODELS[model], "-s", "4"],
            cwd=ESRGAN.parent, capture_output=True, text=True, errors="replace",
        )
        if result.returncode != 0 or not tmp_out.exists():
            sys.exit(f"[오류] AI 업스케일 실패: {result.stderr[-500:]}")
        img = Image.open(tmp_out)
        img.load()
    # 모델은 항상 4배로 키우므로, 다른 배율은 원본 기준 크기로 맞춘다
    with Image.open(src) as orig:
        target = (round(orig.width * scale), round(orig.height * scale))
    if img.size != target:
        img = img.resize(target, Image.LANCZOS)
    return img


def find_grid(edges, axis):
    """경계선 분포에서 반복 주기(도트 한 칸 크기)와 시작 위치를 찾는다. (점수, 주기, 오프셋)"""
    prof = edges.sum(axis=axis).astype(float)
    prof -= prof.mean()
    n = len(prof)
    spec = np.abs(np.fft.rfft(prof, n=4 * n))
    base = spec[1:].mean() + 1e-9
    scored = []
    for p in np.arange(2.0, 40.0, 0.05):
        scored.append((spec[int(round(4 * n / p))] / base, p))
    top = max(s for s, _ in scored)
    if top < GRID_SCORE_MIN:
        return top, None, 0.0
    # 배음(주기의 1/2, 1/3...)도 점수가 높으므로, 최고점에 가까운 것 중 가장 큰 주기를 고른다
    score, period = max(((s, p) for s, p in scored if s >= top * 0.75), key=lambda sp: sp[1])
    pos = np.arange(n) + 1  # edges[i] 는 i 와 i+1 사이 경계
    phase = np.angle((prof * np.exp(-2j * np.pi * pos / period)).sum())
    offset = (-phase * period / (2 * np.pi)) % period
    return score, period, offset


def cell_bounds(size, period, offset):
    edges = np.arange(offset - period, size + period, period)
    bounds = [(max(0, int(round(a))), min(size, int(round(b)))) for a, b in zip(edges[:-1], edges[1:])]
    return [(a, b) for a, b in bounds if b - a >= max(1, period * 0.5)]


def analyze(img):
    """이미지를 읽어 어울리는 방식을 고른다. (방식, 설명, 격자정보)"""
    a = np.asarray(img.convert("RGBA")).astype(np.int32)
    rgb, alpha = a[..., :3], a[..., 3]
    vis = alpha > 0
    colors = len(np.unique(rgb[vis].reshape(-1, 3), axis=0)) if vis.any() else 0
    if max(img.size) <= SMALL_PIXEL_MAX and colors <= SMALL_PIXEL_COLORS:
        return "pixel", f"작은 크기({img.width}x{img.height})·적은 색 수({colors}색) → 원본 도트 그림", None
    dx = np.abs(rgb[:, 1:] - rgb[:, :-1]).sum(-1) > 40
    dy = np.abs(rgb[1:] - rgb[:-1]).sum(-1) > 40
    sx, px, ox = find_grid(dx, 0)
    sy, py, oy = find_grid(dy, 1)
    if px and py:
        return "pixel", f"도트 격자 발견 (한 칸 약 {px:.1f}x{py:.1f}px)", (px, ox, py, oy)
    return "ai", f"도트 격자 없음 (점수 {min(sx, sy):.1f}) → 일러스트/애니풍", None


def upscale_pixel(src: Path, scale: float, grid=None):
    img = Image.open(src).convert("RGBA")
    target = (round(img.width * scale), round(img.height * scale))
    if grid:
        # 도트 한 칸마다 가운데 영역의 대표색을 뽑아 원래 해상도의 도트 그림으로 복원
        px, ox, py, oy = grid
        a = np.asarray(img)
        cols, rows = cell_bounds(img.width, px, ox), cell_bounds(img.height, py, oy)
        small = np.zeros((len(rows), len(cols), 4), dtype=np.uint8)
        for j, (y0, y1) in enumerate(rows):
            my = (y1 - y0) // 4
            for i, (x0, x1) in enumerate(cols):
                mx = (x1 - x0) // 4
                cell = a[y0 + my:y1 - my, x0 + mx:x1 - mx].reshape(-1, 4)
                small[j, i] = np.median(cell, axis=0)
        img = Image.fromarray(small, "RGBA")
    return img.resize(target, Image.NEAREST)


def default_out(src: Path, scale: float) -> Path:
    s = int(scale) if scale == int(scale) else scale
    return src.with_name(f"{src.stem}_x{s}{src.suffix}")


def process(src: Path, dst: Path, args):
    mode, grid = args.mode, None
    if mode in ("auto", "pixel"):
        detected, reason, grid = analyze(Image.open(src))
        if mode == "auto":
            mode = detected
            print(f"[판별] {src.name}: {reason} → {mode} 방식")
    if mode == "ai":
        img = upscale_ai(src, dst, args.scale, args.model)
    else:
        img = upscale_pixel(src, args.scale, grid)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.suffix.lower() in (".jpg", ".jpeg"):
        img = img.convert("RGB")
    img.save(dst)
    print(f"[저장] {dst.resolve()} ({img.width}x{img.height})")


def main():
    p = argparse.ArgumentParser(description="이미지 업스케일링")
    p.add_argument("input", help="이미지 파일 또는 폴더")
    p.add_argument("--out", "-o", help="저장 경로 (파일 또는 폴더). 생략 시 원본 옆에 _x배율 로 저장")
    p.add_argument("--scale", "-s", type=float, default=4, help="확대 배율 (기본 4)")
    p.add_argument("--mode", choices=["auto", "ai", "pixel"], default="auto",
                   help="auto(기본, 자동 판별) / ai / pixel(도트용)")
    p.add_argument("--model", choices=list(AI_MODELS), default="anime", help="ai 모드 모델 (기본 anime)")
    args = p.parse_args()

    src = Path(args.input)
    if src.is_dir():
        files = sorted(f for f in src.iterdir() if f.suffix.lower() in IMAGE_EXTS)
        if not files:
            sys.exit(f"[오류] 폴더에 이미지가 없습니다: {src}")
        out_dir = Path(args.out) if args.out else None
        for f in files:
            process(f, (out_dir / f.name) if out_dir else default_out(f, args.scale), args)
    elif src.exists():
        process(src, Path(args.out) if args.out else default_out(src, args.scale), args)
    else:
        sys.exit(f"[오류] 파일이 없습니다: {src}")


if __name__ == "__main__":
    main()
