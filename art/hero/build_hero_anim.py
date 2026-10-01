# -*- coding: utf-8 -*-
"""주인공 모션(대기 4 · 사격 3 프레임)을 게임에 넣는다.
   원본: art/hero/idle_sheet.png · shoot_sheet.png — 나노바나나(flash 512px)가 heroine.png 를 ref 로 한 장에 나란히 그린 스프라이트 시트.
   하는 일: 덩어리(연결 영역)별로 프레임을 자른다(주먹이 옆 프레임에 겹쳐서 세로로 자르면 안 된다) → 시트마다 첫 프레임 키를 HERO_H 의 4배로 맞춘다
   → 발 중심을 기준으로 정렬해 같은 크기 칸에 넣는다 → 가로 한 줄 아틀라스 WebP data URI + 프레임별 주먹 위치(무기가 따라간다)를 index.html 에 쓴다.
   다시 돌려도 같은 결과(멱등). 쓰는 법: python art/hero/build_hero_anim.py [--preview out.gif]"""
import io, os, re, sys, json, base64
from collections import deque
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
P = os.path.join(ROOT, "game", "index.html")
HERO_H, K = 56, 4            # 화면 높이(논리 px) · 아틀라스 배율
FIST0_X = 15                 # 첫 대기 프레임에서 주먹 오른끝 = SURVIVOR_X + 15 (무기 사각형이 x+12 에서 시작)
SHEETS = [("idle", "idle_sheet.png", 4), ("shoot", "shoot_sheet.png", 3)]


def components(mask):
    """4-연결 덩어리. (픽셀 수, ys, xs) 를 큰 순서로."""
    h, w = mask.shape; lab = np.zeros((h, w), np.int32); out = []; n = 0
    for y0, x0 in zip(*np.nonzero(mask)):
        if lab[y0, x0]: continue
        n += 1; lab[y0, x0] = n; q = deque([(y0, x0)]); ys, xs = [], []
        while q:
            y, x = q.popleft(); ys.append(y); xs.append(x)
            for yy, xx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                if 0 <= yy < h and 0 <= xx < w and mask[yy, xx] and not lab[yy, xx]:
                    lab[yy, xx] = n; q.append((yy, xx))
        out.append((len(ys), np.array(ys), np.array(xs)))
    return sorted(out, key=lambda c: -c[0])


def frames_of(path, count):
    im = Image.open(path).convert("RGBA"); a = np.array(im); mask = a[:, :, 3] > 128
    comps = components(mask)
    big, small = comps[:count], comps[count:]
    assert len(big) == count and big[-1][0] > 0.3 * big[0][0], "%s: 프레임 %d개를 못 찾았다" % (path, count)
    owner = [[c] for c in big]
    for c in small:                       # 떨어진 조각(머리카락 끝 등)은 가장 가까운 프레임에 붙인다
        cx = c[2].mean(); owner[int(np.argmin([abs(b[2].mean() - cx) for b in big]))].append(c)
    owner.sort(key=lambda cs: cs[0][2].mean())
    out = []
    for cs in owner:
        ys = np.concatenate([c[1] for c in cs]); xs = np.concatenate([c[2] for c in cs])
        t, b, l, r = ys.min(), ys.max(), xs.min(), xs.max()
        sub = np.zeros((b - t + 1, r - l + 1, 4), np.uint8); sub[ys - t, xs - l] = a[ys, xs]
        out.append(Image.fromarray(sub))
    return out


def body_width(img):
    m = np.array(img)[:, :, 3] > 128; xs = np.nonzero(m[int(m.shape[0] * 0.6)])[0]
    return xs.max() - xs.min()


def measure(img):
    """발 중심 x · 주먹 오른끝 x · 주먹 중심 y (픽셀 좌표)."""
    m = np.array(img)[:, :, 3] > 128; h = m.shape[0]
    foot = m[int(h * 0.9):]; fx = np.nonzero(foot.any(0))[0]
    band = m[int(h * 0.2):int(h * 0.5)]; rx = np.nonzero(band.any(0))[0].max()
    fy = np.nonzero(band[:, max(0, rx - 8):rx + 1].any(1))[0].mean() + int(h * 0.2)
    return (fx.min() + fx.max()) / 2, rx, fy


def build():
    frames = []; ref = None
    for name, f, n in SHEETS:
        fr = frames_of(os.path.join(HERE, f), n)
        # 시트마다 그린 체형이 조금 다르다(사격 시트가 키에 비해 ~10% 통통). 키만 맞추면 커 보여서 키·몸통 폭의 기하평균으로 맞춘다.
        # 첫 시트(대기)는 키를 HERO_H*K 로, 다음 시트는 그 크기에 맞춘다. 시트 안에서는 같은 배율(프레임끼리 차이를 살린다)
        size = np.sqrt(fr[0].height * body_width(fr[0]))
        if ref is None: ref = size * HERO_H * K / fr[0].height
        s = ref / size
        for i, im in enumerate(fr):
            im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
            frames.append((name, i, im, measure(im)))
    left = max(m[0] for *_, m in frames); right = max(im.width - m[0] for _, _, im, m in frames)
    cw, ch = int(np.ceil(left + right)) + 2, max(im.height for _, _, im, _ in frames)
    atlas = Image.new("RGBA", (cw * len(frames), ch), (0, 0, 0, 0)); meta = []
    for k, (name, i, im, (ax, fxr, fyc)) in enumerate(frames):
        ox = round(left - ax) + 1; oy = ch - im.height
        atlas.alpha_composite(im, (k * cw + ox, oy))
        meta.append((name, ox + fxr, oy + fyc))
    # 논리 좌표: 칸 왼쪽 = x + lx, 칸 아래 = fy + 1. 무기는 첫 프레임 주먹 기준 (dx, dy) 만큼 옮긴다
    lx = FIST0_X - meta[0][1] / K
    d = [[round((m[1] - meta[0][1]) / K, 1), round((m[2] - meta[0][2]) / K, 1)] for m in meta]
    return atlas, cw, ch, lx, d, [m[0] for m in meta]


def main():
    atlas, cw, ch, lx, d, names = build()
    b = io.BytesIO(); atlas.save(b, "WEBP", quality=90, method=6)
    idle = [i for i, n in enumerate(names) if n == "idle"]; shoot = [i for i, n in enumerate(names) if n == "shoot"]
    js = ("const HERO_ANIM = { cw: %d, ch: %d, k: %d, lx: %s, idle: %s, shoot: %s, fist: %s,\n"
          "  src: 'data:image/webp;base64,%s' };" % (cw, ch, K, round(lx, 1), json.dumps(idle), json.dumps(shoot),
                                                     json.dumps([[float(v) for v in p] for p in d], separators=(",", ":")), base64.b64encode(b.getvalue()).decode("ascii")))
    t = io.open(P, encoding="utf-8-sig").read()
    t, n = re.subn(r"const HERO_ANIM = \{.*?\n  src: '[^']*' \};", lambda m: js, t, flags=re.S)
    assert n == 1, "HERO_ANIM 블록을 못 찾았다"
    io.open(P, "w", encoding="utf-8", newline="").write(t)
    print("ok atlas %dx%d (%d frames, cell %dx%d) %d bytes, lx=%.1f fist=%s" % (atlas.width, ch, len(names), cw, ch, len(b.getvalue()), lx, d))
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]; seq = idle * 2 + shoot + [shoot[0]] + idle
        fr = []
        for i in seq:
            bg = Image.new("RGBA", (cw, ch), (48, 52, 46, 255)); bg.alpha_composite(atlas.crop((i * cw, 0, (i + 1) * cw, ch))); fr.append(bg.convert("P", palette=Image.ADAPTIVE))
        fr[0].save(out, save_all=True, append_images=fr[1:], duration=[200 if seq[j] in idle else 70 for j in range(len(seq))], loop=0)


if __name__ == "__main__":
    main()
