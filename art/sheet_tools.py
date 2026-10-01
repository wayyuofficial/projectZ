# -*- coding: utf-8 -*-
"""나노바나나 시트 → 게임 data URI 공통 도구 (M9 0.2). art/*/build_*.py 가 쓴다.

- bands(occ, gap)          : 1차원 점유 배열을 gap 픽셀 이상 빈 곳에서 나눈 구간들
- grid_cells(a, gap)       : 투명 아닌 픽셀의 가로·세로 빈 띠로 줄·칸 상자 [(y0,y1,x0,x1), ...] 줄마다
- merge_to(row, n)         : 칸이 n 개보다 많으면 가장 가까운 이웃끼리 합친다(흩어진 불꽃·머리카락)
- components(mask)         : 4-연결 덩어리 [(ys, xs), ...]
- crop_alpha(a, box)       : 상자 안에서 투명 아닌 부분만 잘라 Image
- webp_uri(im, w, h, q)    : 크기 바꿔 WebP data URI
- replace_block(name, js)  : index.html 의 `const NAME = {` ~ `};` 블록을 바꾼다. **한 줄에 항목 하나** 형식만 맞춘다
                             (빈 블록에서 아래 코드를 삼키지 않게 — 2026-10-01 무기 빌드 사고)
"""
import io, os, re, base64
from collections import deque
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "game", "index.html")


def bands(occ, gap):
    idx = np.nonzero(occ)[0]; out = []
    if not len(idx): return out
    s = p = idx[0]
    for i in idx[1:]:
        if i - p > gap: out.append((s, p + 1)); s = i
        p = i
    out.append((s, p + 1)); return out


def grid_cells(a, gap=14, alpha=40):
    m = a[..., 3] > alpha; rows = []
    for y0, y1 in bands(m.any(1), gap):
        rows.append([(y0, y1, x0, x1) for x0, x1 in bands(m[y0:y1].any(0), gap)])
    return rows


def merge_to(row, n):
    row = list(row)
    while len(row) > n:
        g = min(range(len(row) - 1), key=lambda i: row[i + 1][2] - row[i][3])
        a, b = row[g], row[g + 1]; row[g:g + 2] = [(min(a[0], b[0]), max(a[1], b[1]), a[2], b[3])]
    return row


def components(mask):
    h, w = mask.shape; lab = np.zeros((h, w), np.int32); out = []; n = 0
    for y0, x0 in zip(*np.nonzero(mask)):
        if lab[y0, x0]: continue
        n += 1; lab[y0, x0] = n; q = deque([(y0, x0)]); ys, xs = [], []
        while q:
            y, x = q.popleft(); ys.append(y); xs.append(x)
            for yy, xx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                if 0 <= yy < h and 0 <= xx < w and mask[yy, xx] and not lab[yy, xx]:
                    lab[yy, xx] = n; q.append((yy, xx))
        out.append((np.array(ys), np.array(xs)))
    return out


def crop_alpha(a, box, alpha=40):
    y0, y1, x0, x1 = box; sub = a[y0:y1, x0:x1]; ys, xs = np.nonzero(sub[..., 3] > alpha)
    return Image.fromarray(sub[ys.min():ys.max() + 1, xs.min():xs.max() + 1])


def webp_uri(im, w=None, h=None, q=88):
    if w or h:
        w = w or round(im.width * h / im.height); h = h or round(im.height * w / im.width)
        im = im.resize((max(1, int(w)), max(1, int(h))), Image.LANCZOS)
    b = io.BytesIO(); im.save(b, "WEBP", quality=q, method=6)
    return "data:image/webp;base64," + base64.b64encode(b.getvalue()).decode("ascii")


def replace_block(name, js, path=GAME):
    """js 는 `const NAME = {\\n  k: ...\\n};` 형식(한 줄에 항목 하나)."""
    t = io.open(path, encoding="utf-8-sig").read()
    t, n = re.subn(r"const %s = \{\n(?:  [\w$]+: [^\n]*\n)*\};" % re.escape(name), lambda m: js, t)
    assert n == 1, "%s 블록을 못 찾았다" % name
    io.open(path, "w", encoding="utf-8", newline="").write(t)


def block_js(name, items):
    """items: [(키, JS 값 문자열)] → 한 줄에 하나."""
    return "const %s = {\n%s\n};" % (name, ",\n".join("  %s: %s" % kv for kv in items))
