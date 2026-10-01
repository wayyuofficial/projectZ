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
from sheet_tools import grid_cells, merge_to, crop_alpha, components, webp_uri, replace_block, block_js

HERE = os.path.dirname(os.path.abspath(__file__))
ZH, K, Q = 54, 3, 85             # 화면 키(논리 px, 주인공 56) · 배율 · WebP 품질
BANDS = ["city", "subway", "factory", "forest", "base", "lab"]   # BG_BANDS 순서
FRAMES = 6


def frames_of(path):
    """프레임 6개. 덩어리로 자른다 — 앞으로 뻗은 손이 옆 프레임 칸까지 들어가서 칸으로 자르면 옆 좀비 손이 묻는다.
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
            out.append(Image.fromarray(sub).transpose(Image.FLIP_LEFT_RIGHT))
        return out
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
        out.append(Image.fromarray(sub[ys.min():ys.max() + 1, xs2.min():xs2.max() + 1]).transpose(Image.FLIP_LEFT_RIGHT))
    return out


def foot_x(im):
    m = np.array(im)[..., 3] > 128; h = m.shape[0]
    xs = np.nonzero(m[int(h * 0.9):].any(0))[0]
    return (xs.min() + xs.max()) / 2


def main():
    files = sorted(glob.glob(os.path.join(HERE, "*_*.png")))
    by_band = {b: [f for f in files if os.path.basename(f).startswith(b + "_")] for b in BANDS}
    items, report = [], {}
    for b in BANDS:
        types = []
        for f in by_band[b]:
            fr = frames_of(f); s = ZH * K / fr[0].height
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
