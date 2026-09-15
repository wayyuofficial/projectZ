# -*- coding: utf-8 -*-
"""측정용 가짜 사람이 돈을 쥐고 안 쓰는지 — **산출물이 아니라 자를 본다.**

검사 21개가 전부 산출물(게임·계획서·기록)을 보고 있었다. 아무도 **자**를 안 봤다.
2026-09-16 에 `tools/sim_port.py` 의 `auto_run` 이 무기 값을 `parts` 와 견주고
결제는 `plans` 로 하고 있었다. 못 살 무기가 "가장 싼 것" 으로 뽑히면 그 틱이 통째로
멈춰서, **구역 29 에서 부품 98억을 손에 쥔 채 아무것도 안 샀다.**

차단도 경고도 안 떴다. 나온 숫자(구역 30 도달 180.9분)가 그럴듯해서 **8일 동안 안 걸렸다.**
그 사이 밸런스를 세 번 그 숫자에 맞춰 고쳤다. 자를 고치니 40.9분이 나왔다.
사례: cases/2026-09-16-22-자가고장난측정도구.md

근거가 규칙이 아니라 **사례**다 (그 패턴은 아직 1회라 절차 40 이 승격을 막는다).
절차 40 4 항: 근거가 사례면 PRIORITY = 1.

## 무엇을 보는가

`auto_run` 은 매수를 끝낸 직후 **살 수 있는 게 남아 있는지** 스스로 센다(`idle_buy`).
매수 루프는 "더 못 살 때까지" 도는 것이므로 그 수는 **언제나 0 이어야 한다.**
0 이 아니면 고르는 줄과 결제하는 줄이 어긋난 것이다.

세는 자리를 검사가 아니라 도구 안에 둔 이유: 여기서 매수 루프를 다시 짜면
**자가 둘이 되어** 지금 잡은 것과 똑같은 방식으로 갈라진다.

1순위다 — 이게 틀리면 밸런스 판정 전부가 같은 방향으로 틀린다.
"""
NAME = "측정용 가짜 사람이 살 수 있는데 안 샀는지 (자를 본다)"
PRIORITY = 1

import os, sys, json, subprocess

# **딴 프로세스에서 돌린다.** 같은 프로세스에서 import 하면 c16 등이 먼저 불러 둔
# sys.modules 의 낡은 sim_port 를 보게 된다 — 검사의 대상은 **지금 디스크에 있는 파일**이다.
SNIPPET = (
    "import sys, json;"
    "sys.path.insert(0, sys.argv[1]);"
    "import sim_port as S;"
    "r = S.auto_run(seed=1, max_min=60);"
    "print(json.dumps({'idle': r.get('idle_buy', -1), 'zone': r['final_zone']}))"
)


def run(root):
    tools = os.path.join(root, "tools")
    if not os.path.exists(os.path.join(tools, "sim_port.py")):
        return {"status": "skip", "detail": ["tools/sim_port.py 가 없다"]}

    r = subprocess.run([sys.executable, "-c", SNIPPET, tools],
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        # 포트 자체가 깨진 것은 c16 이 말한다. 여기서 두 번 말하지 않는다.
        return {"status": "skip",
                "detail": ["auto_run 을 못 돌렸다 (c16 을 보라): %s"
                           % (r.stderr or "").strip().splitlines()[-1:]]}
    try:
        out = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        return {"status": "fail", "detail": ["auto_run 의 출력을 못 읽었다: %r" % r.stdout[-200:]]}

    if out["idle"] < 0:
        return {"status": "fail",
                "detail": ["auto_run 이 idle_buy 를 안 돌려준다 — 자가 자기를 안 센다.",
                           "sim_port.auto_run 의 매수 뒤 세는 줄을 지우지 마라 (c22)"]}

    if out["idle"] > 0:
        return {"status": "fail",
                "detail": ["매수를 끝낸 직후에 **살 수 있는 게 남은 틱이 %d회**다." % out["idle"],
                           "가짜 사람이 돈을 쥐고 안 쓴다 — 고르는 줄과 결제하는 줄이 어긋났다.",
                           "재화가 둘이면(부품·설계도) 값을 통화끼리 견주면 안 된다.",
                           "sim_port.auto_run 을 보라. 사례: cases/2026-09-16-22-자가고장난측정도구.md"]}

    return {"status": "ok",
            "detail": ["60분 런에서 돈을 쥐고 안 산 틱 0회 (구역 %d 도달)" % out["zone"]]}
