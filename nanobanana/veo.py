"""Veo(Gemini 영상 모델)로 짧은 영상 생성. 이미지 → 영상, 첫·끝 장면 지정 가능.

사용 예:
  python veo.py "she raises her arms and aims" --first start.png --last end.png --out clip.mp4
  python veo.py "a slime bouncing" --model lite --seconds 4 --out slime.mp4

API 키: nanobanana.py 와 같다 (환경변수 GEMINI_API_KEY 또는 옆의 .env). 영상은 초 단위로 과금된다 — 짧게 시작할 것.
"""
import argparse
import sys
import time
from pathlib import Path

from nanobanana import load_api_key

MODELS = {
    "lite": "veo-3.1-lite-generate-preview",
    "fast": "veo-3.1-fast-generate-preview",
    "full": "veo-3.1-generate-preview",
}


def image_arg(types, path):
    data = Path(path).read_bytes()
    mime = "image/jpeg" if path.lower().endswith((".jpg", ".jpeg")) else "image/png"
    return types.Image(image_bytes=data, mime_type=mime)


def main():
    p = argparse.ArgumentParser(description="Veo 로 영상 생성")
    p.add_argument("prompt")
    p.add_argument("--out", "-o", default="output.mp4")
    p.add_argument("--first", "-f", help="첫 장면 이미지")
    p.add_argument("--last", "-l", help="끝 장면 이미지 (--first 와 함께)")
    p.add_argument("--model", "-m", default="fast", help=f"모델 ID 또는 별칭 {list(MODELS)} (기본 fast)")
    p.add_argument("--seconds", "-s", type=int, default=6, choices=[4, 6, 8])
    p.add_argument("--aspect", "-a", default="16:9", choices=["16:9", "9:16"])
    p.add_argument("--resolution", "-r", default="720p", choices=["720p", "1080p"])
    p.add_argument("--negative", "-n", help="피할 내용")
    args = p.parse_args()

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=load_api_key())
    cfg = dict(aspect_ratio=args.aspect, duration_seconds=args.seconds, resolution=args.resolution, number_of_videos=1)
    if args.negative:
        cfg["negative_prompt"] = args.negative
    if args.last:
        if not args.first:
            sys.exit("[오류] --last 는 --first 와 함께 쓴다")
        cfg["last_frame"] = image_arg(types, args.last)
        if args.seconds != 8:   # 2026-10-01 실측: 첫·끝+6초(+negative) 는 400 "use case is currently not supported", 첫·끝+8초는 됐다
            print("[알림] --last 를 쓰면 8초만 지원 — 8초로 바꿉니다")
            cfg["duration_seconds"] = 8
    model = MODELS.get(args.model, args.model)
    try:
        op = client.models.generate_videos(
            model=model, prompt=args.prompt,
            image=image_arg(types, args.first) if args.first else None,
            config=types.GenerateVideosConfig(**cfg))
        t0 = time.time()
        while not op.done:
            time.sleep(10)
            op = client.operations.get(op)
            print(f"[대기] {int(time.time() - t0)}초", flush=True)
    except Exception as e:
        sys.exit(f"[오류] API 호출 실패: {e}")
    if op.error:
        sys.exit(f"[오류] 생성 실패: {op.error}")
    vids = op.response.generated_videos if op.response else None
    if not vids:
        sys.exit(f"[오류] 영상이 없습니다 (필터됨?): {op.response}")
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    client.files.download(file=vids[0].video)
    vids[0].video.save(str(out))
    print(f"[저장] {out.resolve()} ({model}, {args.seconds}초)")


if __name__ == "__main__":
    main()
