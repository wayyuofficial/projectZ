# -*- coding: utf-8 -*-
"""밸런스 표가 게임 상수와 어긋났는지.

근거: cases/2026-09-08-10-검증자분리.md — 8.1 에서 게임 상수를 재보정하고
`plans/balance-zones.csv` 를 안 고쳐 **10개 구역이 전부 틀린 값**으로 남아 있었다.
잘못된 숫자가 저장소에 살아 있는 것이 가장 위험하다.

이 검사는 `tools/gen_balance_csv.py` 를 믿지 않는다. **직접 다시 계산해서 비교한다.**
생성기를 import 하면 생성기가 틀렸을 때 같이 틀린다.

1순위다. 판단이 갈리는 문제가 아니라 숫자가 맞거나 틀리거나다.
"""
NAME = "밸런스 표가 게임 상수와 맞는지"
PRIORITY = 1

import io, os, re, math


def run(root):
    game = os.path.join(root, "game", "index.html")
    csv = os.path.join(root, "plans", "balance-zones.csv")
    if not os.path.exists(game):
        return {"status": "skip", "detail": ["game/index.html 이 없다"]}
    if not os.path.exists(csv):
        return {"status": "fail", "detail": ["plans/balance-zones.csv 가 없다"]}

    with io.open(game, encoding="utf-8-sig", errors="replace") as f:
        t = f.read()

    def num(pat, label):
        m = re.search(pat, t)
        if not m:
            raise ValueError("게임에서 %s 를 못 찾았다" % label)
        return float(m.group(1))

    try:
        hp0 = num(r"const ZONE_HP0\s*=\s*([\d.]+)", "ZONE_HP0")
        hpg = num(r"ZONE_HP_G\s*=\s*([\d.]+)", "ZONE_HP_G")
        rw0 = num(r"const ZONE_RW0\s*=\s*([\d.]+)", "ZONE_RW0")
        rwg = num(r"ZONE_RW_G\s*=\s*([\d.]+)", "ZONE_RW_G")
        dpr = num(r"const ZOMBIE_DPS_RATIO\s*=\s*([\d.]+)", "ZOMBIE_DPS_RATIO")
        zones = int(num(r"const ZONE_COUNT\s*=\s*(\d+)", "ZONE_COUNT"))
        wall_every = int(num(r"const WALL_EVERY\s*=\s*(\d+)", "WALL_EVERY"))     # M2 벽: 처치당 보상 ÷ 처치배수
        wall_kills = num(r"WALL_KILL_MULT\s*=\s*(\d+)", "WALL_KILL_MULT")
        wall_start = int(num(r"WALL_START\s*=\s*(\d+)", "WALL_START"))
    except ValueError as e:
        return {"status": "error", "detail": [str(e)]}

    with io.open(csv, encoding="utf-8-sig", errors="replace") as f:
        lines = [l.strip() for l in f if l.strip()]
    body = lines[1:]

    bad = []
    if len(body) != zones:
        bad.append("표의 행 수 %d 개, 게임의 구역 수 %d 개 — 다르다" % (len(body), zones))

    for i, line in enumerate(body[:zones]):
        cols = line.split(",")
        if len(cols) < 4:
            bad.append("%d번째 행의 칸이 모자라다: %s" % (i + 1, line))
            continue
        z = i + 1
        want_hp = round(hp0 * hpg ** (z - 1))   # M2 벽은 HP 가 아니라 처치 수라 표의 HP 는 기본 곡선이다
        want_dps = round(hp0 * hpg ** (z - 1) * dpr)
        want_rw = round(rw0 * rwg ** (z - 1) / (wall_kills if (z >= wall_start and z % wall_every == 0) else 1), 1)   # M2 벽 (구역 10 부터)
        try:
            got_hp, got_dps, got_rw = int(cols[1]), int(cols[2]), float(cols[3])
        except ValueError:
            bad.append("%d번째 행의 숫자를 못 읽었다: %s" % (z, line))
            continue
        if got_hp != want_hp:
            bad.append("구역%d 좀비HP 표 %s vs 게임 %s" % (z, got_hp, want_hp))
        if got_dps != want_dps:
            bad.append("구역%d 좀비DPS 표 %s vs 게임 %s" % (z, got_dps, want_dps))
        if abs(got_rw - want_rw) > 0.05:
            bad.append("구역%d 처치보상 표 %s vs 게임 %s" % (z, got_rw, want_rw))

    if bad:
        bad = bad[:8] + (["… 외 %d건" % (len(bad) - 8)] if len(bad) > 8 else [])
        bad.append("python tools/gen_balance_csv.py 로 다시 만든다")
        return {"status": "fail", "detail": bad}
    return {"status": "ok", "detail": ["구역 %d개 표와 게임 상수 일치" % zones]}
