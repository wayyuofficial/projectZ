# -*- coding: utf-8 -*-
"""무기 그림 11종을 게임에 넣는다 (손에 든 무기 + 아이콘).
   원본: sheet_a.png · sheet_b.png — 나노바나나(flash 512px)가 한 장에 여러 무기를 그린 시트. sheet_a 는 주인공(heroine.png)을,
   sheet_b 는 sheet_a 를 ref 로 해 화풍을 맞췄다. 쇠파이프 종류는 일반 등급 = 권총(pistol), 고급 이상 = 쌍권총(dual) — 그림만 다르다.
   하는 일: 덩어리별로 무기를 잘라(읽는 순서: 위→아래, 왼→오) art/weapons/<id>.png 로 저장 → 손에 든 길이(논리 px)의 4배로 줄여
   WebP data URI + 손잡이 위치(주먹이 쥘 곳)를 index.html 의 WEAPON_ART 에 쓴다. 다시 돌려도 같은 결과(멱등).
   쓰는 법: python art/weapons/build_weapons.py"""
import io, os, re, json, base64
from collections import deque
import numpy as np
from PIL import Image
import sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sheet_tools import components, replace_block   # M9 0.2 공통 도구

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
P = os.path.join(ROOT, "game", "index.html")
K = 4                                      # 배율(고해상도 화면용)
# 시트 → 읽는 순서대로 무기 id (None = 안 쓴다)
SHEETS = [
    ("sheet_a.png", ["pistol", "dual", "rifle", "shotgun", "flamer", "crossbow"]),
    ("sheet_b.png", ["mine", "mg", None, "launcher", "saw", "rail"]),       # 3번째는 요청 안 한 소총이 하나 더 나왔다
]
# id → (손에 든 길이 논리 px, 손잡이 x·y 비율). 손잡이 = 주먹이 오는 점. 게임에서 눈으로 맞춘 값
ART = {
    "pistol":   (17, 0.30, 0.62),
    "dual":     (19, 0.30, 0.62),
    "rifle":    (38, 0.36, 0.55),
    "shotgun":  (38, 0.36, 0.55),
    "flamer":   (36, 0.24, 0.45),
    "crossbow": (34, 0.40, 0.55),
    "mine":     (15, 0.45, 0.65),
    "mg":       (42, 0.26, 0.60),
    "launcher": (36, 0.30, 0.62),
    "saw":      (40, 0.22, 0.45),
    "rail":     (44, 0.24, 0.62),
}


def items(path, count):
    a = np.array(Image.open(path).convert("RGBA")); comps = components(a[..., 3] > 128)
    comps.sort(key=lambda c: -len(c[0]))
    big, small = comps[:count], comps[count:]
    groups = [[c] for c in big]
    for c in small:                        # 떨어진 조각(화살촉·불씨 등)은 상자가 가장 가까운 무기에 붙인다
        cy, cx = c[0].mean(), c[1].mean()
        d = [max(0, b[1].min() - cx, cx - b[1].max()) + max(0, b[0].min() - cy, cy - b[0].max()) for b in big]
        if min(d) < 12: groups[int(np.argmin(d))].append(c)
    boxes = []
    for g in groups:
        ys = np.concatenate([c[0] for c in g]); xs = np.concatenate([c[1] for c in g])
        sub = np.zeros((ys.max() - ys.min() + 1, xs.max() - xs.min() + 1, 4), np.uint8)
        sub[ys - ys.min(), xs - xs.min()] = a[ys, xs]
        boxes.append((ys.min(), xs.min(), Image.fromarray(sub)))
    rows = []                              # 읽는 순서: 위쪽 줄부터(같은 줄 = 윗변 차이 < 60), 줄 안에선 왼쪽부터
    for b in sorted(boxes, key=lambda b: b[0]):
        if rows and abs(rows[-1][0][0] - b[0]) < 60: rows[-1].append(b)
        else: rows.append([b])
    return [b[2] for r in rows for b in sorted(r, key=lambda b: b[1])]


def main():
    art = {}
    for f, ids in SHEETS:
        for wid, im in zip(ids, items(os.path.join(HERE, f), len(ids))):
            if wid is None: continue
            im.save(os.path.join(HERE, wid + ".png"))
            L, gx, gy = ART[wid]
            w = L * K; h = max(1, round(im.height * w / im.width))
            b = io.BytesIO(); im.resize((w, h), Image.LANCZOS).save(b, "WEBP", quality=90, method=6)
            art[wid] = (L, round(h / K, 2), gx, gy, base64.b64encode(b.getvalue()).decode("ascii"))
    missing = set(ART) - set(art); assert not missing, "못 찾은 무기: %s" % missing
    rows = ",\n".join("  %s: { w: %d, h: %s, gx: %s, gy: %s, src: 'data:image/webp;base64,%s' }" % (k, *art[k]) for k in ART)
    js = "const WEAPON_ART = {\n" + rows + "\n};"
    replace_block("WEAPON_ART", js)
    print("ok", {k: "%dx%s" % (v[0], v[1]) for k, v in art.items()}, sum(len(v[4]) for v in art.values()), "chars")


if __name__ == "__main__":
    main()
