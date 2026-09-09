# -*- coding: utf-8 -*-
"""파이썬 포트가 게임과 어긋났는지.

근거: 2026-09-09 8차 감사. 감사 회차마다 포트를 새로 짜다 보니
**같은 게임을 두고 두 포트가 구역5 도달 시간에서 25% 어긋났다**
(만든 쪽 9.5분 vs 검증자 7.6분, 범위가 겹치지도 않았다).
숫자가 두 개면 둘 다 못 쓴다. 그래서 포트를 `tools/sim_port.py` 하나로 모았다.

포트는 게임의 거울이다. 거울은 원본이 바뀌면 깨진다.
이 검사는 `tools/sim_port.py` 의 `MIRRORED` 에 적힌 함수들의 본문을
`game/index.html` 에서 **직접 다시 떠서** 해시를 비교한다.

**포트를 import 하지 않는다.** import 하면 포트가 틀렸을 때 같이 틀린다 (c13 과 같은 이유).
`MIRRORED` 는 글자로 읽고, 본문 추출과 해시는 여기서 다시 한다.

**1순위다.** 어긋난 포트로 잰 숫자는 측정이 아니라 추측이다 (불변 원칙 1).
게임을 고쳤으면 포트도 손으로 맞춘 뒤 `python tools/sim_port.py --reseal` 로 다시 찍는다.

## 이 검사가 못 막는 것 (숨기지 않는다)
**해시가 맞아도 파이썬 구현이 원본과 같다는 보장은 없다.** 처음 옮길 때 잘못 옮겼으면
그대로 봉인된다. 이 검사가 막는 것은 "게임을 고치고 포트를 안 고치는 것" 하나다.
포트가 원본과 같은지는 사람이 나란히 놓고 읽어야 한다.
"""
NAME = "파이썬 포트가 게임과 어긋났는지"
PRIORITY = 1

import io, os, re, hashlib

# 포트가 반드시 게임에서 뽑아 써야 하는 상수. 여기에 숫자를 베껴 적으면 조용히 어긋난다.
MUST_EXTRACT = ["ZONE_HP0", "ZONE_HP_G", "ZONE_RW0", "ZONE_RW_G", "ZOMBIE_DPS_RATIO",
                "ZONE_COUNT", "KILLS_PER_ZONE", "BOSS_EVERY", "BOSS_HP_MULT",
                "MAX_ONSCREEN_ZOMBIES", "OFFLINE_MAX_HOURS", "OFFLINE_RATE"]


def js_function(src, name):
    m = re.search(r"^function\s+" + name + r"\s*\(", src, re.M)
    if not m:
        return None
    i = src.index("{", m.end() - 1)
    depth, j = 0, i
    while j < len(src):
        c = src[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return src[m.start():j + 1]
        j += 1
    return None


def run(root):
    game = os.path.join(root, "game", "index.html")
    port = os.path.join(root, "tools", "sim_port.py")
    if not os.path.exists(port):
        return {"status": "skip", "detail": ["tools/sim_port.py 가 없다"]}
    if not os.path.exists(game):
        return {"status": "skip", "detail": ["game/index.html 이 없다"]}

    with io.open(game, encoding="utf-8-sig", errors="replace") as f:
        src = f.read()
    with io.open(port, encoding="utf-8", errors="replace") as f:
        ptxt = f.read()

    m = re.search(r"^MIRRORED = \{(.*?)^\}", ptxt, re.S | re.M)
    if not m:
        return {"status": "fail", "detail": ["tools/sim_port.py 에서 MIRRORED 를 못 찾았다"]}
    sealed = dict(re.findall(r'"(\w+)"\s*:\s*"([0-9a-f]{16})"', m.group(1)))
    if not sealed:
        return {"status": "fail", "detail": ["MIRRORED 가 비어 있다 — 무엇도 잠기지 않았다"]}

    bad = []
    for name in sorted(sealed):
        body = js_function(src, name)
        if body is None:
            bad.append("%s : game/index.html 에 이 함수가 없다 — 이름이 바뀌었는가?" % name)
            continue
        got = hashlib.sha256(re.sub(r"\s+", " ", body).strip().encode("utf-8")).hexdigest()[:16]
        if got != sealed[name]:
            bad.append("%s : 게임이 바뀌었다 (잠금 %s / 현재 %s)" % (name, sealed[name], got))

    for c in MUST_EXTRACT:
        if not re.search(r'num\(\s*"%s"\s*\)' % c, ptxt):
            bad.append("%s 를 game/index.html 에서 뽑지 않는다 — 포트에 숫자를 베껴 적었는가?" % c)

    if bad:
        bad = bad[:10] + (["… 외 %d건" % (len(bad) - 10)] if len(bad) > 10 else [])
        bad.append("포트를 손으로 다시 맞춘 뒤 python tools/sim_port.py --reseal 로 잠금을 갱신한다")
        bad.append("게임을 고치고 포트를 안 고치면 그 뒤 측정은 전부 못 쓴다")
        return {"status": "fail", "detail": bad}
    return {"status": "ok", "detail": ["옮긴 함수 %d개가 게임과 일치" % len(sealed)]}
