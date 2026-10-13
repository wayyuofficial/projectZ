# -*- coding: utf-8 -*-
"""UI 그림을 게임에 넣는다 (M9 3·4) — 카드 틀 · 보급 상자 · 버튼/패널 틀 · UI 아이콘.
   원본: art/ui/sheet_*.png — 나노바나나(flash 512px). 무기 시트(art/weapons/sheet_a.png)를 ref 로 화풍을 맞췄다.
   틀(9칸 늘리기): 투명 아닌 부분만 잘라 가로 W 로 줄이고, 테두리 두께(가운데 줄에서 처음 투명해지는 곳)를 inset 으로 적는다.
   UI_ART 에 한 줄씩. 없는 시트는 건너뛴다. 다시 돌려도 같은 결과(멱등). 쓰는 법: python art/ui/build_ui.py"""
import os, sys, json
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sheet_tools import grid_cells, merge_to, crop_alpha, row_frames, webp_uri, replace_block, block_js

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


def tile(name, sheet, W):
    """이음새 없는 무늬 한 장 — 가로세로 W 로 줄인다(바탕에 createPattern 으로 깐다)."""
    p = os.path.join(HERE, sheet)
    if not os.path.exists(p): return
    im = Image.open(p).convert("RGB").resize((W, W), Image.LANCZOS)
    items.append((name, json.dumps({"w": W, "h": W, "src": webp_uri(im, q=80)}, separators=(",", ":"))))


def strip(name, sheet, n, H):
    """한 줄 n 프레임 애니메이션(보급 상자). 같은 배율, 가로 가운데·바닥 맞춤, 칸 = 가장 큰 프레임."""
    p = os.path.join(HERE, sheet)
    if not os.path.exists(p): return
    fr = row_frames(p, n, flip=False); s = H / max(im.height for im in fr)
    fr = [im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS) for im in fr]
    cw, ch = max(im.width for im in fr), max(im.height for im in fr)
    atlas = Image.new("RGBA", (cw * n, ch))
    for i, im in enumerate(fr): atlas.alpha_composite(im, (i * cw + (cw - im.width) // 2, ch - im.height))
    items.append((name, json.dumps({"cw": cw, "ch": ch, "n": n, "src": webp_uri(atlas, q=88)}, separators=(",", ":"))))


def icons(sheet, cols, kinds, L=24, K=4):
    """아이콘 격자(줄마다 cols 칸, 읽는 순서 = kinds). 키 = icon_<kind, ':' → '_'>. 긴 변 L(논리 px)의 K 배."""
    p = os.path.join(HERE, sheet)
    if not os.path.exists(p): return
    a = np.array(Image.open(p).convert("RGBA")); rows = grid_cells(a, 10)
    cells = [c for r in rows for c in merge_to(r, cols)]
    assert len(cells) >= len(kinds), "%s: 칸 %d개 (기대 %d)" % (sheet, len(cells), len(kinds))
    for kind, c in zip(kinds, cells):
        im = crop_alpha(a, c); s = L * K / max(im.size); w, h = round(im.width * s), round(im.height * s)
        items.append(("icon_" + kind.replace(":", "_"), json.dumps({"w": round(w / K, 2), "h": round(h / K, 2), "src": webp_uri(im, w, h, 90)}, separators=(",", ":"))))


def main():
    frame("card", "sheet_card_frame.png", 120)
    frame("btn", "sheet_btn_frame_rust.png", 220)   # M21 (지시 #185) — 녹슨 철판 틀. 옛 강철 틀은 sheet_btn_frame.png
    tile("rust", "sheet_rust_tile.png", 192)        # M21 — 이음새 없는 녹 무늬(버튼·탭·상단 바·아래 판 바탕)
    strip("crate", "sheet_crate.png", 3, 240)
    icons("sheet_icons_a.png", 4, ["stat", "weapon", "gear", "daily", "c:parts", "c:plans", "s:atk", "s:spd", "s:hp", "s:reg", "s:inc", "s:crit"])
    icons("sheet_icons_b.png", 3, ["s:cdmg", "d:login", "d:quest", "d:supply", "d:reset", "boss", "revive", "clock", "key"])
    icons("sheet_icons_c.png", 4, ["k:focus", "k:grenade", "k:adren", "k:aid", "k:molotov", "k:pierce", "k:turret", "k:strike", "k:book", "skill", "rebirth"])   # M12 2.1 (지시 #160)
    replace_block("UI_ART", block_js("UI_ART", items))
    print("ok", len(items), "items", [k for k, _ in items], sum(len(v) for _, v in items), "chars")


if __name__ == "__main__":
    main()
