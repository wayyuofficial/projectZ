# -*- coding: utf-8 -*-
"""거울(sim_port)의 저장 상태가 게임의 freshState 와 같은 칸을 갖는지 — **자를 본다.**

근거: 사례 26 (2026-09-18). M6 2단계에서 거울 freshState 의 한 줄 끝에 주석을 붙이다 그 줄의
`day·maxDay·quest·questTaken` 이 주석 안으로 들어갔다. 파이썬은 아무 말 없이 돌았고, 거울의 과제는
한 번도 안 채워졌다(과제 보상 설계도 0). 그 상태로 곡선(128.3분)을 재고 예측 M6-B1 이야기까지 했다.
c16 은 게임 본문의 해시만 보므로 **거울 쪽이 조용히 깨진 것**은 못 본다. quest_pace 가 KeyError 로 죽어서야 드러났다.

## 무엇을 보는가
게임 `freshState()` 가 돌려주는 객체의 **1층 키** 전부가 거울 `Sim.freshState()` 에도 있는가.
(거울에만 있는 키는 허용 — 측정용 보조 칸일 수 있다.)

딴 프로세스에서 거울을 불러온다 (c22 와 같은 이유 — 이 프로세스의 sys.modules 에 낡은 sim_port 가 있을 수 있다).
"""
NAME = "거울의 저장 상태가 게임 freshState 와 같은 칸을 갖는지 (자를 본다)"
PRIORITY = 1

import io, os, re, sys, json, subprocess

SNIPPET = (
    "import sys, json;"
    "sys.path.insert(0, sys.argv[1]);"
    "import sim_port as S;"
    "print(json.dumps(sorted(S.Sim(seed=1).freshState().keys())))"
)


def _game_keys(txt):
    m = re.search(r"function freshState\(\)\s*\{\s*return\s*\{(.*?)\n\s*\};", txt, re.S)
    if not m:
        return None
    body = m.group(1)
    # 1층 키만: 중괄호·대괄호 깊이 0 에서 `이름:` 을 센다
    keys, depth, i, n = [], 0, 0, len(body)
    while i < n:
        c = body[i]
        if c in "{[":
            depth += 1
        elif c in "}]":
            depth -= 1
        elif depth == 0 and (c.isalpha() or c == "_"):
            j = i
            while j < n and (body[j].isalnum() or body[j] == "_"):
                j += 1
            k = j
            while k < n and body[k] in " \t":
                k += 1
            if k < n and body[k] == ":":
                keys.append(body[i:j]); i = k; continue
            i = j; continue
        elif c == "/" and body[i:i + 2] == "//":
            j = body.find("\n", i); i = n if j < 0 else j; continue
        elif c == "/" and body[i:i + 2] == "/*":
            j = body.find("*/", i); i = n if j < 0 else j + 2; continue
        i += 1
    return sorted(set(keys))


def run(root):
    game = os.path.join(root, "game", "index.html")
    tools = os.path.join(root, "tools")
    if not os.path.exists(game) or not os.path.exists(os.path.join(tools, "sim_port.py")):
        return {"status": "skip", "detail": ["game/index.html 또는 tools/sim_port.py 가 없다"]}
    gk = _game_keys(io.open(game, encoding="utf-8-sig").read())
    if gk is None:
        return {"status": "skip", "detail": ["게임에서 freshState() 를 못 찾았다"]}
    r = subprocess.run([sys.executable, "-c", SNIPPET, tools], capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        return {"status": "skip", "detail": ["거울을 못 불러왔다 (c16 을 보라): %s" % (r.stderr or "").strip().splitlines()[-1:]]}
    try:
        pk = set(json.loads(r.stdout.strip().splitlines()[-1]))
    except Exception:
        return {"status": "fail", "detail": ["거울 freshState 출력을 못 읽었다: %r" % r.stdout[-200:]]}
    missing = [k for k in gk if k not in pk]
    if missing:
        return {"status": "fail", "detail": ["거울 freshState 에 없는 게임 저장 칸: %s — 거울이 그 칸을 모르면 그 기능은 측정에서 사라진다 (사례 26)" % missing,
                                             "tools/sim_port.py 의 freshState 를 게임과 나란히 놓고 고쳐라"]}
    return {"status": "ok", "detail": ["게임 저장 칸 %d개가 거울에 전부 있다 (거울에만 있는 칸 %d)" % (len(gk), len(pk - set(gk)))]}
