# -*- coding: utf-8 -*-
"""M15 (지시 #164, 분석 B2) — 자주 보는 구역 1~10 배경을 **가로로 긴 그림**으로 다시 그린다.
   M13 스크롤은 그림 + 좌우 뒤집은 그림을 이어 붙여서 큰 건물이 거울처럼 되풀이돼 보였다.
   나노바나나로 21:9 파노라마를 그리고(지금 구역 그림을 --ref 로 — 같은 장소·화풍), 오른쪽 끝을 왼쪽 처음과 겹쳐 섞어 **끝없이 이어지는** 그림으로 만든다.
   원본은 wide/zNN_raw.png, 이어 붙일 수 있게 만든 것은 wide/zNN.png(높이 384). 이미 있는 원본은 건너뛴다(다시 돌려도 과금 안 됨).
   쓰는 법: python art/bg/gen_wide.py [구역 ...]"""
import os, subprocess, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.environ.get("NANOBANANA") or os.path.join(os.path.dirname(os.path.dirname(HERE)), "nanobanana", "nanobanana.py")
OUT = os.path.join(HERE, "wide")
H = 384            # 게임은 이 높이를 전투 영역 폭(540)만큼으로 늘린다 — 정사각 그림(512 → 540)과 같은 크기로 보인다
BLEND = 0.12       # 끝과 처음을 섞는 폭(그림 폭의 비율)
STYLE = ("Same place, same pixel art style and same palette as the reference image. 16-bit retro pixel art, crisp hard-edged pixels, "
         "very wide panoramic side-scrolling 2D game background seen from the side, the scene continues naturally to the left and right with varied buildings, "
         "no single big symmetric landmark in the middle. The lower fifth is a flat walkable floor running straight across the full width. "
         "Upper third is empty sky or dark ceiling with haze. Muted, desaturated, low contrast so game characters stand out in front. "
         "No characters, no people, no zombies, no animals, no text, no letters, no UI, no border. Scene: ")
def _scenes():   # gen_zones.py 의 장면 문구(구역 2~60)를 읽기만 한다 — import 하면 그 파일의 생성 반복이 돈다
    import ast, io
    src = io.open(os.path.join(HERE, "gen_zones.py"), encoding="utf-8").read()
    node = next(n for n in ast.parse(src).body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "ZONES")
    return ast.literal_eval(node.value)
SCENES = _scenes()
SCENES.setdefault(1, "ruined apartment street of a destroyed city at grey dawn, cracked walls, wrecked cars, sandbags, fallen signs, rubble")


def make_loop(raw_path, out_path):
    im = Image.open(raw_path).convert("RGB")
    w = round(im.width * H / im.height)
    im = im.resize((w, H), Image.NEAREST)
    k = max(8, int(w * BLEND))
    body = im.crop((0, 0, w - k, H))           # 끝 k 픽셀을 처음 k 픽셀과 섞어 앞에 덮는다 → 오른쪽 끝 다음에 왼쪽 처음이 이어진다
    tail = im.crop((w - k, 0, w, H)); head = body.crop((0, 0, k, H))
    mask = Image.linear_gradient("L").rotate(-90, expand=True).resize((k, H))   # 왼쪽 255(꼬리) → 오른쪽 0(처음) — rotate(90) 이면 거꾸로라 이음매가 k 에 생긴다(z01 첫 시험에서 봤다)
    mixed = Image.composite(tail, head, mask)
    body.paste(mixed, (0, 0))
    body.save(out_path)
    return body.size


def main(zs):
    os.makedirs(OUT, exist_ok=True)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    for z in zs:
        raw = os.path.join(OUT, "z%02d_raw.png" % z)
        ref = os.path.join(HERE, "zones", "z%02d.png" % z)
        if not os.path.exists(raw):
            r = subprocess.run([sys.executable, TOOL, STYLE + SCENES[z], "--ref", ref, "--aspect", "21:9", "--size", "1K", "--out", raw], env=env)
            if r.returncode != 0 or not os.path.exists(raw):
                print("구역 %d 실패" % z); continue
        print("구역 %d → %s" % (z, make_loop(raw, os.path.join(OUT, "z%02d.png" % z))))


if __name__ == "__main__":
    main([int(a) for a in sys.argv[1:]] or list(range(1, 11)))
