# -*- coding: utf-8 -*-
"""단일 파일 유지 — 게임 HTML이 외부 파일을 참조하면 래핑 때 검은 화면이 된다.

근거: 형식 결정(단일 HTML 캔버스 → WebView 래핑). 사례가 아니라 결정이라 2순위.
"""
NAME = "게임 HTML이 외부 파일을 참조하는지"
PRIORITY = 2

import io, os, re, glob

SCRIPT_SRC = re.compile(r"<script[^>]*\ssrc\s*=", re.I)
LINK_HREF = re.compile(r"<link[^>]*\shref\s*=", re.I)
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

    if bad:
        return {"status": "warn", "detail": bad}
    return {"status": "ok", "detail": ["게임 %d개가 단일 파일 유지" % len(games)]}
