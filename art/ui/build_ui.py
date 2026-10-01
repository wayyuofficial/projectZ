# -*- coding: utf-8 -*-
"""UI 그림을 게임에 넣는다 (M9 3·4) — 카드 틀 · 보급 상자 · 버튼/패널 틀 · UI 아이콘.
   원본: art/ui/sheet_*.png — 나노바나나(flash 512px). 무기 시트(art/weapons/sheet_a.png)를 ref 로 화풍을 맞췄다.
   틀(9칸 늘리기): 투명 아닌 부분만 잘라 가로 W 로 줄이고, 테두리 두께(가운데 줄에서 처음 투명해지는 곳)를 inset 으로 적는다.
   UI_ART 에 한 줄씩. 없는 시트는 건너뛴다. 다시 돌려도 같은 결과(멱등). 쓰는 법: python art/ui/build_ui.py"""
import os, sys, json
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sheet_tools import grid_cells, merge_to, crop_alpha, webp_uri, replace_block, block_js

HERE = os.path.dirname(os.path.abspath(__file__))
items = []


def frame(name, sheet, W):
    """9칸 틀. inset = 테두리 두께(줄인 그림 픽셀)."""
    p = os.path.join(HERE, sheet)
    if not os.path.exists(p): return
    a = np.array(Image.open(p).convert("RGBA")); im = crop_alpha(a, (0, a.shape[0], 0, a.shape[1]))
    s = W / im.width; im = im.resize((W, round(im.height * s)), Image.LANCZOS)
    m = np.array(im)[..., 3] > 40; cy, cx = m.shape[0] // 2, m.shape[1] // 2
    inset = min(int(np.argmin(m[cy, :cx])), int(np.argmin(m[:cy, cx]))) + 1   # 왼쪽·위에서 처음 비는 곳
    items.append((name, json.dumps({"w": im.width, "h": im.height, "inset": inset, "src": webp_uri(im, q=90)}, separators=(",", ":"))))


def main():
    frame("card", "sheet_card_frame.png", 120)
    replace_block("UI_ART", block_js("UI_ART", items))
    print("ok", [(k, json.loads(v)["w"], json.loads(v)["h"], json.loads(v).get("inset")) for k, v in items], sum(len(v) for _, v in items), "chars")


if __name__ == "__main__":
    main()
