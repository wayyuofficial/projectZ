# -*- coding: utf-8 -*-
"""이 환경에 없는 파이썬 명령을 절차서·검사·도구가 쓰고 있는지.

근거: cases/2026-09-08-03-조용한실패.md (실측 관측).
이 환경에는 python 하나만 있다. 다른 이름을 쓰면 오류 없이 조용히 실패한다.
"""
NAME = "이 환경에 없는 파이썬 명령을 쓰는지"
PRIORITY = 1

import io, os, glob

NEEDLE = "py" + "thon3"   # 자기 자신이 걸리지 않도록 쪼개서 만든다
SCAN_DIRS = ["procedures", "checks", "tools"]
EXT = (".md", ".py", ".txt", ".ps1", ".sh", ".bat")


def run(root):
    bad = []
    scanned = 0
    for d in SCAN_DIRS:
        for p in glob.glob(os.path.join(root, d, "**", "*"), recursive=True):
            if not os.path.isfile(p) or not p.lower().endswith(EXT):
                continue
            scanned += 1
            rel = os.path.relpath(p, root).replace(os.sep, "/")
            with io.open(p, encoding="utf-8", errors="replace") as f:
                for i, line in enumerate(f, 1):
                    if NEEDLE in line:
                        bad.append("%s:%d — 이 환경에 없는 명령. python 을 써라 (관측 #3)"
                                   % (rel, i))

    if not scanned:
        return {"status": "skip", "detail": ["검사할 파일이 없다"]}
    if bad:
        return {"status": "fail", "detail": bad}
    return {"status": "ok", "detail": ["파일 %d개 통과" % scanned]}
