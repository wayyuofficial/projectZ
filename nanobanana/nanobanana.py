"""나노바나나(Gemini 이미지 모델) 이미지 생성 도구.

사용 예:
  python nanobanana.py "귀여운 도트 슬라임 몬스터" --out assets/slime.png
  python nanobanana.py "이 캐릭터를 파란 갑옷으로" --ref hero.png --out hero_blue.png
  python nanobanana.py "숲 배경" --aspect 16:9 --size 2K --out bg_forest.png
  python nanobanana.py "불꽃 마법사 스프라이트" --transparent --out mage.png

API 키: 환경변수 GEMINI_API_KEY 또는 이 파일 옆의 .env 파일 (GEMINI_API_KEY=...)
"""
import argparse
import os
import sys
from io import BytesIO
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_MODEL = "gemini-3.1-flash-image"
DEFAULT_SIZE = "512px"  # flash 모델일 때만 적용 (lite/pro는 512px 미지원)
MODELS = {
    "lite": "gemini-3.1-flash-lite-image",  # 가장 빠르고 저렴 (1K만)
    "flash": "gemini-3.1-flash-image",      # 기본
    "pro": "gemini-3-pro-image",            # 고품질
    "legacy": "gemini-2.5-flash-image",
}
ASPECTS = ["1:1", "3:2", "2:3", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"]
SIZES = ["512px", "1K", "2K", "4K"]
KEY_COLOR = (0, 255, 0)  # --transparent 용 크로마키 배경색


def load_api_key():
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    env_file = HERE / ".env"
    if not key and env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            name, _, value = line.partition("=")
            if name.strip() in ("GEMINI_API_KEY", "GOOGLE_API_KEY") and value.strip():
                key = value.strip().strip('"').strip("'")
                break
    if not key:
        sys.exit(f"[오류] API 키가 없습니다. {env_file} 에 GEMINI_API_KEY=키값 을 적어주세요.")
    return key


def remove_key_background(img, tolerance=90):
    """초록 배경(#00FF00)을 투명하게 만든다."""
    img = img.convert("RGBA")
    px = img.load()
    kr, kg, kb = KEY_COLOR
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = px[x, y]
            dist = abs(r - kr) + abs(g - kg) + abs(b - kb)
            if dist < tolerance:
                px[x, y] = (r, g, b, 0)
            elif g > r + 40 and g > b + 40:  # 가장자리 초록 번짐 제거
                px[x, y] = (r, min(g, max(r, b)), b, a)
    # 이미지 테두리의 잡티(모서리 워터마크 등) 제거
    border = 8
    for y in range(img.height):
        for x in range(img.width):
            if x < border or y < border or x >= img.width - border or y >= img.height - border:
                r, g, b, a = px[x, y]
                px[x, y] = (r, g, b, 0)
    return img


def trim(img, pad=4):
    """투명 여백을 잘라 피사체 크기에 딱 맞춘다."""
    bbox = img.getchannel("A").getbbox()
    if not bbox:
        return img
    l, t, r, b = bbox
    return img.crop((max(l - pad, 0), max(t - pad, 0), min(r + pad, img.width), min(b + pad, img.height)))


def unique_path(path: Path, index: int, count: int) -> Path:
    if count > 1:
        path = path.with_name(f"{path.stem}_{index + 1}{path.suffix}")
    return path


def main():
    p = argparse.ArgumentParser(description="나노바나나로 이미지 생성/편집")
    p.add_argument("prompt", help="만들 이미지 설명")
    p.add_argument("--out", "-o", default="output.png", help="저장 경로 (기본 output.png)")
    p.add_argument("--ref", "-r", action="append", default=[], help="참고/편집할 이미지 (여러 번 지정 가능)")
    p.add_argument("--aspect", "-a", choices=ASPECTS, help="가로세로 비율")
    p.add_argument("--size", "-s", choices=SIZES,
                   help=f"해상도 (flash 기본 {DEFAULT_SIZE}, lite/pro 기본 1K)")
    p.add_argument("--model", "-m", default=DEFAULT_MODEL,
                   help=f"모델 ID 또는 별칭 {list(MODELS)} (기본 {DEFAULT_MODEL})")
    p.add_argument("--count", "-n", type=int, default=1, help="생성 개수")
    p.add_argument("--transparent", "-t", action="store_true",
                   help="배경을 투명 PNG로 (초록 배경으로 그린 뒤 제거)")
    p.add_argument("--no-trim", action="store_true",
                   help="--transparent 사용 시 투명 여백 자르기를 하지 않음")
    args = p.parse_args()

    from google import genai
    from google.genai import types
    from PIL import Image

    model = MODELS.get(args.model, args.model)
    prompt = args.prompt
    if args.transparent:
        prompt += (". Place the subject on a perfectly flat, solid pure green (#00FF00) background "
                   "with no shadows, gradients, or green tones on the subject itself.")

    contents = [prompt]
    for ref in args.ref:
        contents.append(Image.open(ref))

    image_cfg = {}
    if args.aspect:
        image_cfg["aspect_ratio"] = args.aspect
    size = args.size or (DEFAULT_SIZE if model == DEFAULT_MODEL else None)
    if size:
        image_cfg["image_size"] = size
    config = types.GenerateContentConfig(
        response_modalities=["IMAGE", "TEXT"],
        image_config=types.ImageConfig(**image_cfg) if image_cfg else None,
    )

    client = genai.Client(api_key=load_api_key())
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    saved = []
    for i in range(args.count):
        try:
            resp = client.models.generate_content(model=model, contents=contents, config=config)
        except Exception as e:
            msg = str(e)
            if "free_tier" in msg and "limit: 0" in msg:
                sys.exit("[오류] 이 모델은 무료 사용량이 0입니다. Google AI Studio에서 결제(Billing)를 연결해야 합니다: "
                         "https://aistudio.google.com/apikey")
            if "prepayment credits" in msg:
                sys.exit("[오류] 선불 크레딧이 없습니다. AI Studio에서 크레딧을 충전하세요: https://ai.studio/projects")
            if "RESOURCE_EXHAUSTED" in msg:
                sys.exit("[오류] 사용량 한도 초과. 잠시 후 다시 시도하세요. 현황: https://ai.dev/rate-limit")
            sys.exit(f"[오류] API 호출 실패: {msg}")
        img_bytes, text = None, []
        for part in (resp.candidates[0].content.parts if resp.candidates and resp.candidates[0].content else []):
            if part.inline_data and part.inline_data.data:
                img_bytes = part.inline_data.data
            elif part.text:
                text.append(part.text)
        if not img_bytes:
            reason = resp.candidates[0].finish_reason if resp.candidates else resp.prompt_feedback
            sys.exit(f"[오류] 이미지가 생성되지 않았습니다. 사유: {reason} {' '.join(text)}")
        img = Image.open(BytesIO(img_bytes))
        if args.transparent:
            img = remove_key_background(img)
            if not args.no_trim:
                img = trim(img)
        path = unique_path(out, i, args.count)
        if path.suffix.lower() in (".jpg", ".jpeg"):
            img = img.convert("RGB")
        img.save(path)
        saved.append(path)
        print(f"[저장] {path.resolve()} ({img.width}x{img.height})")
        if text:
            print("[모델 메모]", " ".join(text).strip())
    return saved


if __name__ == "__main__":
    main()
