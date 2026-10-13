# -*- coding: utf-8 -*-
"""단일 파일 유지 — 게임 HTML이 외부 파일을 참조하면 래핑 때 검은 화면이 된다.

근거: 형식 결정(단일 HTML 캔버스 → WebView 래핑). 사례가 아니라 결정이라 2순위.

M25 (지시 #190, 2026-10-08) — 사람 결정으로 **그림만** `game/img/` 파일로 뺐다(tools/externalize_art.py).
그래서 이 검사가 하나를 더 본다: 게임 코드가 든 `'img/…'` 경로마다 그 파일이 `game/img/` 에 있는지(없으면 그 그림이 안 보인다),
그리고 그림 data URI 가 게임 안에 다시 생겼는지(그림 도구를 돌리고 빼기를 잊었다). script·link 외부 참조는 여전히 경고.
"""
NAME = "게임 HTML이 외부 파일을 참조하는지"
PRIORITY = 2

import io, os, re, glob

SCRIPT_SRC = re.compile(r"<script[^>]*\ssrc\s*=", re.I)
LINK_HREF = re.compile(r"<link[^>]*\shref\s*=", re.I)
IMG_REF = re.compile(r"""['"]((?:img|snd)/[A-Za-z0-9_.\-]+)['"]""")   # M25
DATA_IMG = re.compile(r"data:image/[a-z]+;base64,")
IMG_SRC = re.compile(r"<img[^>]*\ssrc\s*=\s*[\"'](?!data:)", re.I)


def run(root):
    games = sorted(glob.glob(os.path.join(root, "game", "*.html")))
    if not games:
        return {"status": "skip", "detail": ["game/*.html 이 아직 없다"]}

    bad = []
    for p in games:
        base = os.path.basename(p)
        with io.open(p, encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f, 1):
                if SCRIPT_SRC.search(line):
                    bad.append("%s:%d — 외부 script src" % (base, i))
                if LINK_HREF.search(line):
                    bad.append("%s:%d — 외부 link href" % (base, i))
                if IMG_SRC.search(line):
                    bad.append("%s:%d — 외부 img src (data: URI 로 넣어라)" % (base, i))

        txt = io.open(p, encoding="utf-8", errors="replace").read()
        for r in sorted(set(IMG_REF.findall(txt))):
            if not os.path.exists(os.path.join(os.path.dirname(p), r)):
                bad.append("%s — '%s' 파일이 없다(그 그림이 안 보이거나 소리가 안 난다)" % (base, r))
        left = len(DATA_IMG.findall(txt))
        if left:
            bad.append("%s — 그림 data URI %d개가 게임 안에 있다 — python tools/externalize_art.py 로 빼라(M25)" % (base, left))

    if bad:
        return {"status": "warn", "detail": bad}
    return {"status": "ok", "detail": ["게임 %d개 — 외부 script·link 없음 · img/·snd/ 경로가 가리키는 파일 다 있음 · 남은 그림 data URI 없음" % len(games)]}
