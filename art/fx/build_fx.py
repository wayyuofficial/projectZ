# -*- coding: utf-8 -*-
"""발사 효과 그림을 게임에 넣는다 (탄·화살·유탄·톱날·총구 화염·착탄 불꽃·폭발).
   원본: 나노바나나(flash 512px) 시트 3장 — 무기 시트(art/weapons/sheet_a.png)를 ref 로 화풍을 맞췄다.
     sheet_projectiles.png  · 줄마다 2개: 권총탄·소총 예광탄 / 기관총 예광탄·산탄 / 화살·유탄 / (로켓 — 안 씀)·톱날
     sheet_flash_impact.png · 윗줄 총구 화염 4프레임 · 아랫줄 착탄 불꽃 4프레임
     sheet_explosion.png    · 폭발 6프레임
   자르기: 투명 아닌 픽셀의 가로·세로 빈 띠로 줄과 칸을 나눈다(불꽃은 조각이 흩어져 덩어리로 못 자른다).
   크기: 화면 크기(논리 px)의 4배. 애니메이션은 시트 안 같은 배율. FX_ART 를 index.html 에 쓴다(멱등).
   쓰는 법: python art/fx/build_fx.py"""
import io, os, re, json, base64
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
P = os.path.join(ROOT, "game", "index.html")
K = 4
# 시트 → 줄마다 이름(None = 안 씀). 값 = 화면 길이(논리 px, 가장 긴 변). 애니메이션은 [이름, 프레임 수, 가장 큰 프레임 길이]
SHEETS = {
    "sheet_projectiles.png": [[("bullet", 9), ("tracer", 24)], [("tracer_mg", 20), ("pellet", 4)],
                              [("bolt", 18), ("grenade", 9)], [(None, 0), ("sawblade", 15)]],
    "sheet_flash_impact.png": [("muzzle", 4, 18), ("impact", 4, 18)],
    "sheet_explosion.png": [("boom", 6, 46)],
}


def bands(occ, gap):
    """1차원 점유 배열에서 gap 픽셀 이상 비어 있는 곳으로 나눈 구간들."""
    idx = np.nonzero(occ)[0]; out = []
    if not len(idx): return out
    s = p = idx[0]
    for i in idx[1:]:
        if i - p > gap: out.append((s, p + 1)); s = i
        p = i
    out.append((s, p + 1)); return out


def cells(path):
    a = np.array(Image.open(path).convert("RGBA")); m = a[..., 3] > 40
    rows = []
    for y0, y1 in bands(m.any(1), 14):
        sub = m[y0:y1]; cols = bands(sub.any(0), 14)
        rows.append([(y0, y1, x0, x1) for x0, x1 in cols])
    return a, rows


def crop(a, y0, y1, x0, x1):
    sub = a[y0:y1, x0:x1]; m = sub[..., 3] > 40; ys, xs = np.nonzero(m)
    return Image.fromarray(sub[ys.min():ys.max() + 1, xs.min():xs.max() + 1])


def enc(im, s):
    w, h = max(1, round(im.width * s)), max(1, round(im.height * s))
    b = io.BytesIO(); im.resize((w, h), Image.LANCZOS).save(b, "WEBP", quality=90, method=6)
    return {"w": round(w / K, 2), "h": round(h / K, 2), "src": "data:image/webp;base64," + base64.b64encode(b.getvalue()).decode("ascii")}


def main():
    art = {}
    for f, spec in SHEETS.items():
        a, rows = cells(os.path.join(HERE, f))
        assert len(rows) == len(spec), "%s: 줄 %d개 (기대 %d)" % (f, len(rows), len(spec))
        for row, sp in zip(rows, spec):
            if isinstance(sp, list):                       # 낱개들
                assert len(row) == len(sp), "%s: 칸 %d개 (기대 %d)" % (f, len(row), len(sp))
                for c, (name, L) in zip(row, sp):
                    if not name: continue
                    im = crop(a, *c); art[name] = enc(im, L * K / max(im.size))
            else:                                          # 애니메이션
                name, n, L = sp
                row = list(row)
                while len(row) > n:                        # 흩어진 불꽃이 칸 둘로 쪼개지면 — 가장 가까운 이웃끼리 합친다
                    g = min(range(len(row) - 1), key=lambda i: row[i + 1][2] - row[i][3])
                    a0, b0 = row[g], row[g + 1]; row[g:g + 2] = [(min(a0[0], b0[0]), max(a0[1], b0[1]), a0[2], b0[3])]
                assert len(row) == n, "%s %s: 프레임 %d개 (기대 %d)" % (f, name, len(row), n)
                ims = [crop(a, *c) for c in row]; s = L * K / max(max(i.size) for i in ims)
                art[name] = [enc(i, s) for i in ims]
    lines = ",\n".join("  %s: %s" % (k, json.dumps(v, separators=(",", ":"))) for k, v in art.items())
    js = "const FX_ART = {\n" + lines + "\n};"
    t = io.open(P, encoding="utf-8-sig").read()
    t, n = re.subn(r"const FX_ART = \{\n(?:  \w+: [^\n]*\n)*\};", lambda m: js, t)   # 한 줄에 하나 — 줄 단위로만 맞춘다
    assert n == 1, "FX_ART 블록을 못 찾았다"
    io.open(P, "w", encoding="utf-8", newline="").write(t)
    print("ok", {k: (len(v) if isinstance(v, list) else "%sx%s" % (v["w"], v["h"])) for k, v in art.items()}, len(js), "chars")


if __name__ == "__main__":
    main()
