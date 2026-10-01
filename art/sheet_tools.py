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


def row_frames(path, FRAMES, flip=True):
    """한 줄 FRAMES 프레임 시트(M9 좀비·보스). flip 이면 좌우를 뒤집는다(오른쪽을 보고 그려진 것을 왼쪽으로). 덩어리로 자른다 — 앞으로 뻗은 손이 옆 프레임 칸까지 들어가서 칸으로 자르면 옆 좀비 손이 묻는다.
    가장 큰 덩어리 6개 = 몸, 나머지 조각(떨어진 손가락·머리카락)은 상자가 가장 가까운 몸에 붙인다. 몸끼리 붙어 6개가 안 되면 칸으로 자른다."""
    a = np.array(Image.open(path).convert("RGBA")); m = a[..., 3] > 128
    comps = sorted(components(m), key=lambda c: -len(c[0]))
    big = comps[:FRAMES]
    if len(big) == FRAMES and len(big[-1][0]) > 0.4 * len(big[0][0]):
        groups = [[c] for c in big]
        for c in comps[FRAMES:]:
            cy, cx = c[0].mean(), c[1].mean()
            d = [max(0, b[1].min() - cx, cx - b[1].max()) + max(0, b[0].min() - cy, cy - b[0].max()) for b in big]
            if min(d) < 10: groups[int(np.argmin(d))].append(c)
        groups.sort(key=lambda g: g[0][1].mean())
        out = []
        for g in groups:
            ys = np.concatenate([c[0] for c in g]); xs = np.concatenate([c[1] for c in g])
            sub = np.zeros((ys.max() - ys.min() + 1, xs.max() - xs.min() + 1, 4), np.uint8)
            sub[ys - ys.min(), xs - xs.min()] = a[ys, xs]
            out.append(Image.fromarray(sub))
        return [im.transpose(Image.FLIP_LEFT_RIGHT) for im in out] if flip else out
    # 몸끼리 닿았다 — 프레임 경계 근처(±1/4 폭)에서 픽셀이 가장 적은 세로줄로 자르고, 조각마다 가장 큰 덩어리(+가까운 조각)만 남긴다
    print("  [가는 목으로 자름]", os.path.basename(path))
    xs = np.nonzero(m.any(0))[0]; x0, x1 = xs.min(), xs.max() + 1; W = (x1 - x0) / FRAMES; col = m.sum(0)
    cuts = [x0]
    for i in range(1, FRAMES):
        c = int(x0 + i * W); lo, hi = int(c - W / 4), int(c + W / 4)
        cuts.append(lo + int(np.argmin(col[lo:hi])))
    cuts.append(x1)
    out = []
    for i in range(FRAMES):
        sub = a[:, cuts[i]:cuts[i + 1]].copy(); sm = sub[..., 3] > 128
        cs = sorted(components(sm), key=lambda c: -len(c[0])); keep = np.zeros_like(sm); body = cs[0]
        keep[body[0], body[1]] = True; near = keep.copy()
        for _ in range(2):                                   # 몸에서 2px 안에 닿는 조각만(옆 프레임 손은 떨어져 있다)
            g = near.copy(); g[1:] |= near[:-1]; g[:-1] |= near[1:]; g[:, 1:] |= near[:, :-1]; g[:, :-1] |= near[:, 1:]; near = g
        for c in cs[1:]:
            if near[c[0], c[1]].any(): keep[c[0], c[1]] = True
        sub[~keep] = 0; ys, xs2 = np.nonzero(keep)
        out.append(Image.fromarray(sub[ys.min():ys.max() + 1, xs2.min():xs2.max() + 1]))
    return [im.transpose(Image.FLIP_LEFT_RIGHT) for im in out] if flip else out


def foot_x(im):
    """발 중심 x(아래 10% 의 가로 가운데)."""
    m = np.array(im)[..., 3] > 128; h = m.shape[0]
    xs = np.nonzero(m[int(h * 0.9):].any(0))[0]
    return (xs.min() + xs.max()) / 2


def replace_block(name, js, path=GAME):
    """js 는 `const NAME = {\\n  k: ...\\n};` 형식(한 줄에 항목 하나)."""
    t = io.open(path, encoding="utf-8-sig").read()
    t, n = re.subn(r"const %s = \{\n(?:  [\w$]+: [^\n]*\n)*\};" % re.escape(name), lambda m: js, t)
    assert n == 1, "%s 블록을 못 찾았다" % name
    io.open(path, "w", encoding="utf-8", newline="").write(t)


def block_js(name, items):
    """items: [(키, JS 값 문자열)] → 한 줄에 하나."""
    return "const %s = {\n%s\n};" % (name, ",\n".join("  %s: %s" % kv for kv in items))
