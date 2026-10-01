# -*- coding: utf-8 -*-
"""보스 6종(묶음마다 하나 — 구역 5·10·15·20·25·30)을 게임에 넣는다 (M9 2.2).
   원본: art/bosses/<묶음>.png — 나노바나나(flash 512px, 21:9) 한 줄 4프레임(걷기 2 · 돌진 준비 · 돌진), 오른쪽을 본다.
   좀비 첫 시트(art/zombies/city_civilian.png)를 ref 로 화풍을 맞췄다.
   하는 일: 덩어리로 4프레임을 자르고(sheet_tools.row_frames) 좌우를 뒤집는다 → 첫 걷기 프레임 키를 BH 로 → 발 중심 정렬 → 보스마다 가로 한 줄 WebP
   → BOSS_ART 에 한 줄씩. 다시 돌려도 같은 결과(멱등). 쓰는 법: python art/bosses/build_bosses.py [--preview out.png]"""
import os, sys, json
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sheet_tools import row_frames, foot_x, webp_uri, replace_block, block_js

HERE = os.path.dirname(os.path.abspath(__file__))
BH, K, Q, FRAMES = 92, 2.5, 82, 4      # 화면 키(논리 px, 예전 보스 도트 96) · 배율 · 품질 · 프레임
BANDS = ["city", "subway", "factory", "forest", "base", "lab"]


def main():
    items = []
    for b in BANDS:
        fr = row_frames(os.path.join(HERE, b + ".png"), FRAMES)
        s = BH * K / fr[0].height
        fr = [im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS) for im in fr]
        left = max(foot_x(im) for im in fr); right = max(im.width - foot_x(im) for im in fr)
        cw, ch = int(np.ceil(left + right)) + 2, max(im.height for im in fr)
        atlas = Image.new("RGBA", (cw * FRAMES, ch))
        for i, im in enumerate(fr):
            atlas.alpha_composite(im, (i * cw + int(round(left - foot_x(im))) + 1, ch - im.height))
        src = webp_uri(atlas, q=Q)
        items.append((b, json.dumps({"cw": cw, "ch": ch, "k": K, "ax": round(left + 1, 1), "src": src}, separators=(",", ":"))))
        print(b, "%dx%d" % (cw, ch), len(src))
        if "--preview" in sys.argv:
            out = sys.argv[sys.argv.index("--preview") + 1]
            bg = Image.new("RGBA", atlas.size, (48, 52, 46, 255)); bg.alpha_composite(atlas); bg.convert("RGB").save(out.replace(".png", "_%s.png" % b))
    replace_block("BOSS_ART", block_js("BOSS_ART", items))


if __name__ == "__main__":
    main()
