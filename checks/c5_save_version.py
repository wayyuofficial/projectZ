# -*- coding: utf-8 -*-
"""저장 버전 검사.

근거: **예방적 가설**. 과거 실수 없음 확인(지시 #6, 2026-09-08).
사례가 아니라 가설이라 2순위다 — 막지 않고 경고만 한다.
세이브 깨짐 사례가 1건이라도 쌓이면 PRIORITY 를 1로 올린다.
"""
NAME = "저장 스키마 버전 상수가 있는지 (가설)"
PRIORITY = 2

import io, os, re, glob

SAVE_VER = re.compile(r"\bSAVE_VERSION\b")
STORAGE = re.compile(r"\blocalStorage\b")


def run(root):
    games = sorted(glob.glob(os.path.join(root, "game", "*.html")))
    if not games:
        return {"status": "skip",
                "detail": ["game/*.html 이 아직 없다"]}

    bad = []
    for p in games:
        base = os.path.basename(p)
        with io.open(p, encoding="utf-8", errors="replace") as f:
            txt = f.read()
        if not STORAGE.search(txt):
            continue  # 저장을 안 쓰면 볼 것 없음
        if not SAVE_VER.search(txt):
            bad.append("%s : localStorage 를 쓰는데 SAVE_VERSION 상수가 없다" % base)

    if bad:
        bad.append("저장 구조를 바꿀 때 버전을 올리지 않으면 기존 세이브가 깨진다 (가설)")
        return {"status": "warn", "detail": bad}
    return {"status": "ok", "detail": ["게임 %d개 통과" % len(games)]}
