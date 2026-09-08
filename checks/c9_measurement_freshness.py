# -*- coding: utf-8 -*-
"""게임을 고쳐놓고 측정을 다시 하지 않았는지.

밸런스(balance-*.json)와 저장 경로(storage-*.json) 두 기록을 본다.

근거: rules/R002-실행으로판정.md (사례 3회 — 자기채점)
게임 파일이 가장 최근 밸런스 측정 기록보다 새로우면 걸린다.
규약이라 2순위로 시작한다. 이 경고를 무시해 사고가 난 사례가 1건 생기면 1순위로 올린다.
"""
NAME = "게임을 고치고 측정을 다시 안 했는지"
PRIORITY = 2

import io, os, glob, json


def run(root):
    games = sorted(glob.glob(os.path.join(root, "game", "*.html")))
    if not games:
        return {"status": "skip", "detail": ["game/*.html 이 없다"]}

    RECORDS = [
        ("balance-*.json", "밸런스", "게임의 실제 함수로 1런을 돌려라 (R002)"),
        ("storage-*.json", "저장·오프라인", "tools/test_storage.js 를 브라우저 콘솔에서 돌려라 (R002)"),
    ]
    bad = []
    checked = []
    for pattern, label, how in RECORDS:
        recs = sorted(glob.glob(os.path.join(root, "measurements", pattern)))
        if not recs:
            bad.append("%s 측정 기록이 없다 (measurements/%s) — %s" % (label, pattern, how))
            continue
        newest = max(recs, key=os.path.getmtime)
        try:
            with io.open(newest, encoding="utf-8") as f:
                rec = json.load(f)
        except Exception as e:
            bad.append("%s 기록을 읽지 못했다: %s (%s)" % (label, os.path.basename(newest), e))
            continue
        mt = os.path.getmtime(newest)
        for g in games:
            if os.path.getmtime(g) > mt + 1:
                bad.append("%s 가 %s 기록(%s)보다 새롭다 — 다시 재라"
                           % (os.path.basename(g), label, os.path.basename(newest)))
        if "측정일" not in rec:
            bad.append("%s 기록에 [측정일] 이 없다" % label)
        checked.append(os.path.basename(newest))

    if bad:
        return {"status": "warn", "detail": bad}
    return {"status": "ok", "detail": ["측정 기록 최신: " + ", ".join(checked)]}
