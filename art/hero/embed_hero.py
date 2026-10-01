# -*- coding: utf-8 -*-
"""주인공(여자 생존자) 그림을 게임에 넣는다. 원본 art/hero/heroine.png = 나노바나나(flash, 512px) 생성 · 투명 배경 · 빈손 조준 자세.
   무기는 게임이 종류별로 따로 그리므로 그림에는 총이 없다. 화면 높이 HERO_H(56) 의 4배로 줄여 WebP data URI 로(파일 하나 규칙 c6).
   다시 돌려도 같은 결과(멱등). 쓰는 법: python art/hero/embed_hero.py"""
import io, os, re, base64
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
P = os.path.join(ROOT, "game", "index.html")
im = Image.open(os.path.join(HERE, "heroine.png")).convert("RGBA")
h = 56 * 4; w = round(im.width * h / im.height)
im = im.resize((w, h), Image.LANCZOS)
b = io.BytesIO(); im.save(b, "WEBP", quality=90, method=6)
line = "const HERO_IMG_SRC = 'data:image/webp;base64,%s';" % base64.b64encode(b.getvalue()).decode("ascii")
t = io.open(P, encoding="utf-8-sig").read()
t, n = re.subn(r"const HERO_IMG_SRC = '[^']*';", lambda m: line, t)
assert n == 1, "HERO_IMG_SRC 줄을 못 찾았다"
io.open(P, "w", encoding="utf-8", newline="").write(t)
print("ok", w, "x", h, len(b.getvalue()), "bytes")
