# -*- coding: utf-8 -*-
"""주인공 모션을 Veo 영상에서 뽑아 게임에 넣는다.
   원본: art/hero/video/veo_raise.mp4 (서 있다 → 겨눔, 첫·끝 장면 first_stand/first_aim) · veo_shoot.mp4 (겨눈 채 연사, 첫·끝 first_aim).
   veo-3.1-fast 720p 8초 24fps, 초록 크로마키 배경 · 고정 카메라 — 모든 프레임이 같은 좌표라 정렬이 필요 없다.
   하는 일: 프레임 추출(ffmpeg) → 초록 빼기·번짐 제거 → 캐릭터 덩어리만 남김(탄피 조각 제거), 주먹 앞(CUT_X)은 잘라냄(총구 화염 제거)
   → 같은 창으로 잘라 K배 크기로 줄임 → 가로 한 줄 아틀라스 WebP + 프레임별 주먹 위치·무기 표시 여부를 index.html 에 쓴다.
   다시 돌려도 같은 결과(멱등). 쓰는 법: python art/hero/build_hero_video.py [--preview out.gif]   (ffmpeg 필요)"""
import io, os, re, sys, json, glob, base64, shutil, subprocess, tempfile
from collections import deque
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
P = os.path.join(ROOT, "game", "index.html")
HERO_H, K = 56, 3            # 화면 키(논리 px) · 아틀라스 배율
CHAR_H = 560                 # 영상 속 캐릭터 키(first_*.png 를 만들 때 넣은 값)
CUT_X = 770                  # 이 x(영상 좌표) 오른쪽은 총구 화염 — 주먹은 760 을 넘지 않는다
BACK_X = 460                 # 이 x 왼쪽은 등·포니테일 — 탄피 색 제거를 여기서만 한다
ARM_X = 690                  # 이 x 오른쪽은 주먹·소매 끝뿐 — 화염 색 제거를 여기서만 한다
# 쓰는 프레임(0부터, 24fps). 12fps 로 줄여 쓴다(2칸씩).
CLIPS = {
    "stand": ("veo_raise.mp4", list(range(0, 21, 2))),                                  # 숨쉬기 — 앞뒤로 왕복 재생
    "raise": ("veo_raise.mp4", list(range(50, 59, 2)) + [82, 84]),                      # 팔 올리기. 60~80 은 주먹을 얼굴 앞에 모으는 권투 자세라 뺀다
    "fire":  ("veo_shoot.mp4", list(range(29, 58, 2))),                                 # 연사 — 29 와 58 자세가 같아 끊김 없이 돈다
    "walk":  ("veo_walk.mp4", list(range(136, 161, 2))),                                # M13 1.2 (지시 #161) — 제자리 걷기 한 주기(136 ≈ 161, 실루엣 차이가 가장 작은 25프레임)
}
WEAPON_MID = 31              # 기본 무기 사각형(fy-34, 높이 6)의 가운데 = 바닥 위 31px
FIRE_REF = ("veo_shoot.mp4", 29)  # 이 프레임 주먹 오른끝 = SURVIVOR_X + 15 (무기 사각형이 x+12 에서 시작)


def ffmpeg():
    exe = shutil.which("ffmpeg")
    if not exe:
        try:
            import imageio_ffmpeg; exe = imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            sys.exit("ffmpeg 가 없다 — 설치하거나 pip install imageio-ffmpeg")
    return exe


def extract(video, tmp):
    out = os.path.join(tmp, os.path.splitext(video)[0]); os.makedirs(out, exist_ok=True)
    subprocess.run([ffmpeg(), "-loglevel", "error", "-i", os.path.join(HERE, "video", video), os.path.join(out, "%03d.png")], check=True)
    return sorted(glob.glob(os.path.join(out, "*.png")))


def main_blob(mask):
    """가장 큰 4-연결 덩어리만."""
    h, w = mask.shape; seen = np.zeros_like(mask); best = []
    ys, xs = np.nonzero(mask)
    for y0, x0 in zip(ys[::499], xs[::499]):
        if seen[y0, x0]: continue
        q = deque([(y0, x0)]); seen[y0, x0] = 1; pts = []
        while q:
            y, x = q.popleft(); pts.append((y, x))
            for yy, xx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                if 0 <= yy < h and 0 <= xx < w and mask[yy, xx] and not seen[yy, xx]:
                    seen[yy, xx] = 1; q.append((yy, xx))
        if len(pts) > len(best): best = pts
    out = np.zeros_like(mask); p = np.array(best); out[p[:, 0], p[:, 1]] = True
    return out


def key(path):
    """RGBA 배열(영상 좌표). 초록 빼기 + 가장자리 초록 번짐 제거."""
    a = np.array(Image.open(path).convert("RGB")).astype(np.int32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    green = g - np.maximum(r, b)
    fg = green < 60; fg[:, CUT_X:] = False
    # 총구 화염: 채도 높은 주황·노랑이거나 거의 흰색. 피부(파랑 성분이 많다)·머리(어둡다)와 겹치지 않는다. 팔 앞쪽에서만 본다
    flash = ((r > 170) & (g - b > 70)) | (np.minimum(np.minimum(r, g), b) > 235)
    flash |= (r >= g) & (g - b > 40) & (r > 70)        # 화염의 어두운 주황 테두리(소매 올리브는 r < g, 피부는 g-b ≤ 33)
    fg[:, ARM_X:] &= ~flash[:, ARM_X:]
    # 등 뒤로 튄 탄피(회색·흰색)가 포니테일에 닿는다 — 등 뒤 영역에서 무채색 밝은 픽셀은 버린다(셔츠는 이보다 오른쪽)
    mx = np.maximum(np.maximum(r, g), b); mn = np.minimum(np.minimum(r, g), b)
    fg[:, :BACK_X] &= ~((mx - mn < 30) & (mx > 110))[:, :BACK_X]
    # 화염 테두리(어두운 1~3px 고리)는 남는다 — 팔 높이에서 세로로 몇 픽셀 안 되는 열부터 오른쪽은 버린다
    cols = fg[:, ARM_X:].sum(0); thin = np.nonzero(cols < 6)[0]
    if len(thin): fg[:, ARM_X + thin[0]:] = False
    # 탄피는 머리카락에 몇 픽셀로 붙는다 — 한 번 깎아 다리를 끊고 덩어리를 고른 뒤 되살린다
    er = fg.copy(); er[1:] &= fg[:-1]; er[:-1] &= fg[1:]; er[:, 1:] &= fg[:, :-1]; er[:, :-1] &= fg[:, 1:]
    body = main_blob(er)
    grow = body.copy()
    for _ in range(3):
        g_ = grow.copy(); g_[1:] |= grow[:-1]; g_[:-1] |= grow[1:]; g_[:, 1:] |= grow[:, :-1]; g_[:, :-1] |= grow[:, 1:]; grow = g_
    fg &= grow
    alpha = np.where(fg, np.clip((90 - green) * 255 // 60, 0, 255), 0)        # 경계는 반투명
    g2 = np.where(green > 0, np.maximum(r, b) + green // 4, g)                  # 번짐 제거
    return np.dstack([r, np.minimum(g, g2), b, alpha]).astype(np.uint8)


def fist(rgba):
    m = rgba[..., 3] > 128; ys, xs = np.nonzero(m); top = ys.min()
    band = (ys > top + 150) & (ys < top + 330); rx = xs[band].max()
    fy = ys[band & (xs > rx - 12)].mean()
    return rx, fy


def build():
    tmp = tempfile.mkdtemp(); files = {}
    try:
        frames = []                                   # (clip, rgba)
        for clip, (video, idx) in CLIPS.items():
            if video not in files: files[video] = extract(video, tmp)
            for i in idx: frames.append((clip, key(files[video][i])))
        ref = key(files[FIRE_REF[0]][FIRE_REF[1]])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    # 공통 창: 모든 프레임 덩어리를 덮는 상자. 바닥 = 발 끝
    boxes = [np.nonzero(f[..., 3] > 0) for _, f in frames]
    t = min(b[0].min() for b in boxes); bt = max(b[0].max() for b in boxes)
    l = min(b[1].min() for b in boxes); r = max(b[1].max() for b in boxes)
    s = HERO_H * K / CHAR_H
    cw, ch = int(np.ceil((r - l + 1) * s)), int(np.ceil((bt - t + 1) * s))
    atlas = Image.new("RGBA", (cw * len(frames), ch)); meta = []
    rfx, rfy = fist(ref)
    base_dy = (rfy - bt) * s / K + WEAPON_MID   # 기준 프레임 주먹 중심이 무기 사각형 가운데(바닥 위 31px)에 오도록
    for k, (clip, f) in enumerate(frames):
        im = Image.fromarray(f[t:bt + 1, l:r + 1]).resize((cw, ch), Image.LANCZOS)
        atlas.alpha_composite(im, (k * cw, 0))
        fx, fy = fist(f)
        meta.append((clip, round((fx - rfx) * s / K, 1), round((fy - rfy) * s / K + base_dy, 1), bool(fx > rfx - 40)))
    # 논리 좌표: 칸 왼쪽 = SURVIVOR_X + lx, 칸 아래 = 바닥(fy + 1)
    lx = 15 - (rfx - l) * s / K
    return atlas, cw, ch, round(lx, 1), (bt - t + 1) * s / K, meta


def main():
    atlas, cw, ch, lx, dh, meta = build()
    b = io.BytesIO(); atlas.save(b, "WEBP", quality=88, method=6)
    clips = {c: [i for i, m in enumerate(meta) if m[0] == c] for c in CLIPS}
    js = ("const HERO_ANIM = { cw: %d, ch: %d, k: %d, lx: %s, stand: %s, raise: %s, fire: %s, walk: %s,\n"
          "  fist: %s, gun: %s,\n"
          "  src: 'data:image/webp;base64,%s' };" % (
              cw, ch, K, lx, json.dumps(clips["stand"]), json.dumps(clips["raise"]), json.dumps(clips["fire"]), json.dumps(clips["walk"]),
              json.dumps([[float(m[1]), float(m[2])] for m in meta], separators=(",", ":")),
              json.dumps([1 if m[3] else 0 for m in meta], separators=(",", ":")),
              base64.b64encode(b.getvalue()).decode("ascii")))
    t = io.open(P, encoding="utf-8-sig").read()
    t, n = re.subn(r"const HERO_ANIM = \{.*?\n  src: '[^']*' \};", lambda m: js, t, flags=re.S)
    assert n == 1, "HERO_ANIM 블록을 못 찾았다"
    io.open(P, "w", encoding="utf-8", newline="").write(t)
    print("ok atlas %dx%d · %d frames (cell %dx%d) · %d bytes · lx=%s" % (atlas.width, ch, len(meta), cw, ch, len(b.getvalue()), lx))
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        st = clips["stand"]; seq = clips["walk"] * 3 + st + st[::-1] + clips["raise"] + clips["fire"] * 2 + clips["raise"][::-1] + st
        fr = []
        for i in seq:
            bg = Image.new("RGBA", (cw, ch), (48, 52, 46, 255)); bg.alpha_composite(atlas.crop((i * cw, 0, (i + 1) * cw, ch)))
            fr.append(bg.convert("RGB"))
        fr[0].save(out, save_all=True, append_images=fr[1:], duration=83, loop=0)


if __name__ == "__main__":
    main()
