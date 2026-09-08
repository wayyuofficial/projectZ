# -*- coding: utf-8 -*-
"""버튼이 오버레이보다 나중에 그려지는지.

근거: cases/2026-09-08-09-자기채점.md
오버레이(오프라인 팝업 · 사망 화면)가 자기 버튼 위에 그려져 닫을 수가 없었다.

**좁은 검사라는 점을 숨기지 않는다.** 함수 이름에 의존한다.
그래도 결함이 정확히 이 순서 때문에 생겼으므로 그 지점만은 지킨다. 2순위.
"""
NAME = "버튼이 오버레이보다 나중에 그려지는지"
PRIORITY = 2

import io, os, re, glob

OVERLAYS = ["drawDeath", "drawOffline"]
BUTTONS = "drawButtons"


def run(root):
    games = sorted(glob.glob(os.path.join(root, "game", "*.html")))
    if not games:
        return {"status": "skip", "detail": ["game/*.html 이 없다"]}

    bad = []
    checked = 0
    for p in games:
        base = os.path.basename(p)
        with io.open(p, encoding="utf-8-sig", errors="replace") as f:
            txt = f.read()

        m = re.search(r"function\s+draw\s*\(\s*\)\s*\{", txt)
        if not m:
            bad.append("%s : function draw() 를 못 찾았다 (셀 수 없음)" % base)
            continue

        # draw() 본문을 중괄호 짝으로 잘라낸다
        i = txt.index("{", m.start())
        depth = 0
        body = None
        for j in range(i, len(txt)):
            if txt[j] == "{":
                depth += 1
            elif txt[j] == "}":
                depth -= 1
                if depth == 0:
                    body = txt[i:j]
                    break
        if body is None:
            bad.append("%s : draw() 본문을 못 잘랐다" % base)
            continue

        checked += 1
        bi = body.find(BUTTONS + "(")
        if bi < 0:
            bad.append("%s : draw() 안에서 %s() 호출을 못 찾았다" % (base, BUTTONS))
            continue

        for ov in OVERLAYS:
            oi = body.find(ov + "(")
            if oi < 0:
                continue          # 그 오버레이가 없으면 볼 것 없다
            if oi > bi:
                bad.append("%s : %s() 가 %s() 보다 뒤에 그려진다 — 오버레이가 버튼을 덮어 누를 수 없게 된다"
                           % (base, ov, BUTTONS))

    if bad:
        return {"status": "warn", "detail": bad}
    return {"status": "ok", "detail": ["게임 %d개 그리기 순서 통과" % checked]}
