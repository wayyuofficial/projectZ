# -*- coding: utf-8 -*-
"""밸런스 숫자를 바꿔놓고 다시 재보지 않았는지.

근거: rules/R002-실행으로판정.md (사례 3회 — 자기채점)
게임 파일이 가장 최근 밸런스 측정 기록보다 새로우면 걸린다.
규약이라 2순위로 시작한다. 이 경고를 무시해 사고가 난 사례가 1건 생기면 1순위로 올린다.
"""
NAME = "밸런스를 바꾸고 다시 재보지 않았는지"
PRIORITY = 2

import io, os, glob, json


def run(root):
    games = sorted(glob.glob(os.path.join(root, "game", "*.html")))
    if not games:
        return {"status": "skip", "detail": ["game/*.html 이 없다"]}

    recs = sorted(glob.glob(os.path.join(root, "measurements", "balance-*.json")))
    if not recs:
        return {"status": "warn",
                "detail": ["밸런스 측정 기록이 하나도 없다 (measurements/balance-*.json)",
                           "게임의 실제 함수로 1런을 돌려 결과를 남겨라 (R002)"]}

    newest = max(recs, key=os.path.getmtime)
    try:
        with io.open(newest, encoding="utf-8") as f:
            rec = json.load(f)
    except Exception as e:
        return {"status": "error",
                "detail": ["측정 기록을 읽지 못했다: %s" % os.path.basename(newest), str(e)]}

    bad = []
    mt = os.path.getmtime(newest)
    for g in games:
        if os.path.getmtime(g) > mt + 1:
            bad.append("%s 가 측정 기록(%s)보다 새롭다 — 숫자를 바꿨으면 다시 재라"
                       % (os.path.basename(g), os.path.basename(newest)))

    for key in ("측정일", "구역별_도달_분", "판정"):
        if key not in rec:
            bad.append("%s 에 [%s] 항목이 없다" % (os.path.basename(newest), key))

    if bad:
        return {"status": "warn", "detail": bad}
    return {"status": "ok",
            "detail": ["측정 기록 최신: %s" % os.path.basename(newest)]}
