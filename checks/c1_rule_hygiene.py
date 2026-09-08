# -*- coding: utf-8 -*-
"""규칙 파일 위생: 머리 4줄 / 유효기한 만료 / 같은 대상 중복."""
NAME = "규칙 머리 4줄 · 유효기한 · 대상 중복"
PRIORITY = 1

import io, os, glob, datetime

NEED = ["근거:", "충돌검토:", "대상:", "유효기한:"]
HEAD_LINES = 12


def run(root):
    # R000-제목.md 형식만. R*.md 로 잡으면 README.md 가 함께 걸린다(2026-09-08 적발).
    files = sorted(glob.glob(os.path.join(root, "rules", "R[0-9][0-9][0-9]-*.md")))
    if not files:
        return {"status": "skip",
                "detail": ["rules/R*.md 가 없다 — 아직 승격된 규칙이 없음"]}

    bad = []
    targets = {}
    today = datetime.date.today()

    for p in files:
        base = os.path.basename(p)
        with io.open(p, encoding="utf-8") as f:
            head = [l.strip() for l in f.read().splitlines()[:HEAD_LINES]]

        found = {}
        for key in NEED:
            hit = [l for l in head if l.startswith(key)]
            if not hit:
                bad.append("%s : 머리에 [%s] 줄이 없다" % (base, key))
            else:
                found[key] = hit[0][len(key):].strip()

        exp = found.get("유효기한:", "")
        if exp and exp != "없음":
            try:
                if datetime.date.fromisoformat(exp) < today:
                    bad.append("%s : 유효기한 지남 (%s)" % (base, exp))
            except ValueError:
                bad.append("%s : 유효기한이 YYYY-MM-DD 도 [없음] 도 아님 (%s)" % (base, exp))

        tgt = found.get("대상:", "")
        if tgt:
            targets.setdefault(tgt, []).append(base)

    for t, fs in sorted(targets.items()):
        if len(fs) > 1:
            bad.append("대상 [%s] 을 다루는 규칙이 %d개 (중복): %s"
                       % (t, len(fs), ", ".join(fs)))

    if bad:
        return {"status": "fail", "detail": bad}
    return {"status": "ok", "detail": ["규칙 %d개 통과" % len(files)]}
