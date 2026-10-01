# -*- coding: utf-8 -*-
"""M8 (지시 #147) — art/bg/zones/z01~z30.png 를 게임에 넣는다. 도트 그림이라 업스케일(AI)은 안 한다(도트를 뭉갠다) — 512px 원본을 WebP 로.
   게임은 지금 구역 그림만 디코드하고 다음 구역 하나를 미리 읽는다(30장을 한꺼번에 풀지 않는다). 다시 돌려도 같은 결과(멱등).
   쓰는 법: python art/bg/embed_zones.py"""
import io, os, re, base64
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
P = os.path.join(ROOT, "game", "index.html")
t = io.open(P, encoding="utf-8-sig").read()
rows, total = [], 0
for z in range(1, 31):
    f = os.path.join(HERE, "zones", "z%02d.png" % z)
    if not os.path.exists(f):
        continue
    im = Image.open(f).convert("RGB")
    b = io.BytesIO(); im.save(b, "WEBP", quality=82, method=6); total += len(b.getvalue())
    rows.append("  %d: 'data:image/webp;base64,%s'" % (z, base64.b64encode(b.getvalue()).decode("ascii")))
block = ("/* M8 (2026-10-01, 지시 #146·#147) — 사람: \"구역별로 컨셉\" · \"1구역부터 30구역까지 컨셉에 맞춰 배경 이미지를 도트그래픽으로 나노바나나로 생성해서 적용\".\n"
         "   구역 하나 = 장소 하나(`plans/결정요청-M8-구역별컨셉-2026-10-01.md`). 원본 art/bg/zones/zNN.png(나노바나나 512px, 구역 1 을 ref 로 화풍 통일) → WebP data URI. 파일 하나 규칙(c6) 유지.\n"
         "   **지금 구역 그림만 디코드**하고 다음 구역 하나를 미리 읽는다. 없는 구역·디코드 전·실패는 타일 세트로 그린다. 넣기는 art/bg/embed_zones.py. */\n"
         "const BG_IMG_SRC = {\n" + ",\n".join(rows) + "\n};\n"
         "const bgImg = {};\n"
         "function bgImgFor(z) {\n"
         "  for (const k of Object.keys(bgImg)) if (+k !== z && +k !== z + 1) delete bgImg[k];   // 지금·다음 구역만 들고 있는다\n"
         "  for (const n of [z, z + 1]) {\n"
         "    if (bgImg[n] || !BG_IMG_SRC[n]) continue;\n"
         "    const im = new Image(); bgImg[n] = im; im.onload = () => { im.ready = true; if (n === G.zone) bgCache = null; }; im.src = BG_IMG_SRC[n];\n"
         "  }\n"
         "  const p = bgImg[z]; return p && p.ready ? p : null;\n"
         "}\n")
# 처음(지시 #145 판)이면 그 블록, 다시 돌리면 이 블록을 바꾼다
m = re.search(r"/\* M8 1\.3 \(2026-10-01, 지시 #145\).*?\nfor \(const band of Object\.keys\(BG_IMG_SRC\)\) \{\n.*?\n\}\n", t, re.S) \
    or re.search(r"/\* M8 \(2026-10-01, 지시 #146·#147\).*?\n  const p = bgImg\[z\]; return p && p\.ready \? p : null;\n\}\n", t, re.S)
assert m, "배경 이미지 블록을 못 찾았다"
t = t[:m.start()] + block + t[m.end():]
t = t.replace("(bgImg[bgBand(G.zone)] ? 'i' : 't')", "(bgImgFor(G.zone) ? 'i' : 't')")
t = t.replace("  const pic = bgImg[bgBand(G.zone)];", "  const pic = bgImgFor(G.zone);")
t = t.replace("    fg.imageSmoothingEnabled = true;\n    fg.drawImage(pic, 0, top, GAME_W, ih);", "    fg.imageSmoothingEnabled = false;   // 도트 — 최근접으로 늘린다\n    fg.drawImage(pic, 0, top, GAME_W, ih);")
assert "bgImg[bgBand" not in t
io.open(P, "w", encoding="utf-8", newline="").write(t)
print("넣음: 구역 %d장 · WebP 합 %d KB · index.html %d KB" % (len(rows), total // 1024, len(t.encode("utf-8")) // 1024))
