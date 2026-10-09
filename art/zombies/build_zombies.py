# -*- coding: utf-8 -*-
"""좀비 16종(묶음별 2~3종)을 게임에 넣는다 (M9 1.2).
   원본: art/zombies/<묶음>_<종>.png — 나노바나나(flash 512px, 21:9) 한 줄 6프레임(걷기 4 · 공격 2), 오른쪽을 본다.
   첫 장(city_civilian)은 주인공(art/hero/heroine.png)을, 나머지는 첫 장을 ref 로 그렸다(화풍 사슬).
   하는 일: 줄의 빈 띠로 프레임 6개를 자른다 → **좌우를 뒤집는다**(좀비는 왼쪽으로 걷는다) → 종마다 첫 걷기 프레임 키를 ZH 로
   → 발 중심을 칸의 같은 x 에, 발끝을 칸 바닥에 → 묶음마다 가로 한 줄 아틀라스(종 × 6) WebP → ZOMBIE_ART 에 한 줄씩.
   다시 돌려도 같은 결과(멱등). 쓰는 법: python art/zombies/build_zombies.py [--preview out.png]"""
import os, sys, glob, json
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sheet_tools import row_frames, foot_x, webp_uri, replace_block, block_js

HERE = os.path.dirname(os.path.abspath(__file__))
ZH, K, Q = 54, 3, 75             # 화면 키(논리 px, 주인공 56) · 배율 · WebP 품질
BANDS = ["city", "subway", "factory", "forest", "base", "lab", "school", "mart", "park", "prison", "cruise", "nuclear", "bunker", "core"]   # M11: 구역 31~60   # BG_BANDS 순서
FRAMES = 6


def main():
    files = sorted(glob.glob(os.path.join(HERE, "*_*.png")))
    by_band = {b: [f for f in files if os.path.basename(f).startswith(b + "_")] for b in BANDS}
    items, report = [], {}
    for b in BANDS:
        types = []
        for f in by_band[b]:
            fr = row_frames(f, FRAMES); s = ZH * K / fr[0].height
            fr = [im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS) for im in fr]
            types.append((os.path.splitext(os.path.basename(f))[0], fr))
        assert types, "%s 묶음 좀비가 없다" % b
        allf = [im for _, fr in types for im in fr]
        left = max(foot_x(im) for im in allf); right = max(im.width - foot_x(im) for im in allf)
        cw, ch = int(np.ceil(left + right)) + 2, max(im.height for im in allf)
        atlas = Image.new("RGBA", (cw * len(allf), ch))
        for i, im in enumerate(allf):
            atlas.alpha_composite(im, (i * cw + int(round(left - foot_x(im))) + 1, ch - im.height))
        src = webp_uri(atlas, q=Q)
        names = [n for n, _ in types]
        items.append((b, json.dumps({"cw": cw, "ch": ch, "k": K, "ax": round(left + 1, 1), "n": len(types), "names": names, "src": src},
                                    ensure_ascii=False, separators=(",", ":"))))
        report[b] = (names, "%dx%d" % (cw, ch), len(src))
        if "--preview" in sys.argv:
            out = sys.argv[sys.argv.index("--preview") + 1]
            bg = Image.new("RGBA", atlas.size, (48, 52, 46, 255)); bg.alpha_composite(atlas)
            bg.convert("RGB").save(out.replace(".png", "_%s.png" % b))
    replace_block("ZOMBIE_ART", block_js("ZOMBIE_ART", items))
    for b, r in report.items(): print(b, r)
    print("합", sum(r[2] for r in report.values()), "chars")


if __name__ == "__main__":
    main()
