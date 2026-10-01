# -*- coding: utf-8 -*-
"""장비 아이콘 12종(4부위 × 3모양)을 게임에 넣는다 (M9 3.1).
   원본: art/gear/sheet_gear.png — 나노바나나(flash 512px, 3:4) 4줄 × 3칸. 무기 시트(art/weapons/sheet_a.png)를 ref 로 화풍을 맞췄다.
   줄 = 머리·몸·장갑·신발, 칸 = GEAR_SLOTS 의 shapes 순서(모자·투구·방독면 / 재킷·방탄복·코트 / 목장갑·가죽장갑·완갑 / 운동화·군화·부츠).
   장갑·신발은 두 짝이 떨어져 있어 줄마다 가까운 칸끼리 합쳐 3칸으로. 긴 변 L(논리 px)의 4배 WebP → GEAR_ART(키 = 부위_모양번호).
   다시 돌려도 같은 결과(멱등). 쓰는 법: python art/gear/build_gear.py"""
import os, sys, json
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sheet_tools import grid_cells, merge_to, crop_alpha, webp_uri, replace_block, block_js

HERE = os.path.dirname(os.path.abspath(__file__))
SLOTS, L, K = ["head", "body", "hands", "feet"], 24, 4


def main():
    a = np.array(Image.open(os.path.join(HERE, "sheet_gear.png")).convert("RGBA"))
    rows = grid_cells(a, 10)
    assert len(rows) == 4, "줄 %d개 (기대 4)" % len(rows)
    items = []
    for slot, row in zip(SLOTS, rows):
        row = merge_to(row, 3); assert len(row) == 3, "%s 칸 %d개" % (slot, len(row))
        for i, c in enumerate(row):
            im = crop_alpha(a, c); s = L * K / max(im.size); w, h = round(im.width * s), round(im.height * s)
            items.append(("%s_%d" % (slot, i), json.dumps({"w": round(w / K, 2), "h": round(h / K, 2), "src": webp_uri(im, w, h, 90)}, separators=(",", ":"))))
    replace_block("GEAR_ART", block_js("GEAR_ART", items))
    print("ok", [k for k, _ in items], sum(len(v) for _, v in items), "chars")


if __name__ == "__main__":
    main()
