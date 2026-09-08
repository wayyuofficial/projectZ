# -*- coding: utf-8 -*-
"""계획서 위생 — 예측과 반증 조건 없는 계획을 막는다 (불변 원칙 3)."""
NAME = "계획서에 예측·반증 조건이 있는지"
PRIORITY = 1

import io, os, glob


def run(root):
    files = [p for p in sorted(glob.glob(os.path.join(root, "plans", "*.md")))
             if os.path.basename(p).lower() != "readme.md"]
    if not files:
        return {"status": "skip", "detail": ["plans/*.md 가 없다"]}

    bad = []
    for p in files:
        base = os.path.basename(p)
        with io.open(p, encoding="utf-8", errors="replace") as f:
            txt = f.read()
        if "예측" not in txt:
            bad.append("%s : [예측] 이 없다 (원칙 3)" % base)
        if "반증" not in txt:
            bad.append("%s : [반증] 조건이 없다 (원칙 3)" % base)

    if bad:
        return {"status": "fail", "detail": bad}
    return {"status": "ok", "detail": ["계획서 %d개 통과" % len(files)]}
