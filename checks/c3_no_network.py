# -*- coding: utf-8 -*-
"""서버 통신 금지 — 선정 기준 S4(서버 불필요) / 정본 금지목록 5."""
NAME = "게임에 서버 통신이 들어갔는지"
PRIORITY = 1

import io, os, re, glob

PATTERNS = [
    (re.compile(r"\bfetch\s*\("), "fetch()"),
    (re.compile(r"\bXMLHttpRequest\b"), "XMLHttpRequest"),
    (re.compile(r"\bnew\s+WebSocket\b"), "WebSocket"),
    (re.compile(r"\bnew\s+EventSource\b"), "EventSource"),
    (re.compile(r"\bnavigator\s*\.\s*sendBeacon\b"), "sendBeacon"),
]


def run(root):
    games = sorted(glob.glob(os.path.join(root, "game", "*.html")))
    if not games:
        return {"status": "skip",
                "detail": ["game/*.html 이 아직 없다 — 게임을 만들면 이 검사가 살아난다"]}

    bad = []
    for p in games:
        base = os.path.basename(p)
        with io.open(p, encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f, 1):
                for rx, label in PATTERNS:
                    if rx.search(line):
                        bad.append("%s:%d — %s (비행기 모드에서 안 돈다)" % (base, i, label))

    if bad:
        return {"status": "fail", "detail": bad}
    return {"status": "ok", "detail": ["게임 %d개에 서버 통신 없음" % len(games)]}
