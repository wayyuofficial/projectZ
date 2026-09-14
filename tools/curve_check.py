# -*- coding: utf-8 -*-
"""목표 체류 곡선 대 실제 체류 — WBS-M2 1.2.

곡선(정본, plans/GAMEDESIGN.md M2 절): 체류(z) = 4분 x 1.05^z. 5의 배수 구역은 벽 x3.
이 도구는 `tools/sim_port.py` 로 여러 시드를 돌려 구역별 체류(다음 구역 도달 시각 - 이 구역 도달 시각)의 중앙값을 내고
목표와의 비율을 표로 찍는다. **종료 코드 = ±30% 밖인 구역 수** (구역 5~29). 0 이면 곡선 안이다.

  python tools/curve_check.py                 # 벽 포함, 20시드
  python tools/curve_check.py --no-wall       # 벽을 끄고 잰다 (예측 M2-B1 은 벽 없는 곡선이다)
  python tools/curve_check.py --selftest      # 일부러 틀린 상수(보상 성장 1.20)로 실패가 나는지 — R003

포트를 새로 짜지 않는다. auto_run 의 구매 전략(가장 싼 것부터)이 곧 이 곡선의 기준 플레이다 — 광고 부스트 없음.
사람 실측은 부스트를 켤 수 있으니 이 곡선보다 빠를 수 있다(M1 21차 지적). 두 시간대를 섞지 않는다.
"""
import io, os, sys, json, math, argparse, statistics, datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import sim_port as SP

TARGET_BASE, TARGET_G = 4.0, 1.05
TOL = 0.30
ARRIVE_TOL = 0.20      # M2-B1‴: 구역 10 도달 시각을 기준점으로, 11~30 의 상대 도달 시각 ±20%
WALL_MULT_TARGET = 2.0   # 지시 #63: 벽 ×2
WALL_START_TARGET = 10   # 곡선은 구역 10 부터 (1~9 는 M1 실측 그대로)
CURVE_FROM = 10
Z_FROM, Z_TO = 5, 29          # 1~4 는 튜토리얼 구간. 30 은 다음 구역이 없어 체류를 못 잰다


WALL_ON = True     # --no-wall 이면 False. 벽을 끄고 재면 목표에서도 벽을 뺀다 (22차 감사 지적)


def target(z):
    return TARGET_BASE * TARGET_G ** z * (WALL_MULT_TARGET if (WALL_ON and z >= WALL_START_TARGET and z % 5 == 0) else 1)


def target_arrive(z):
    """구역 10 도달을 0 으로 놓은 목표 누적 (지시 #63: 곡선은 10~30 만)."""
    return sum(target(k) for k in range(CURVE_FROM, z))


def measure(seeds, wall=True, max_min=900):
    keep = SP.WALL_KILL_MULT
    if not wall:
        SP.WALL_KILL_MULT = 1
    try:
        rows = [SP.auto_run(seed=s, max_min=max_min) for s in seeds]
    finally:
        SP.WALL_KILL_MULT = keep
    stay = {}
    for z in range(1, SP.ZONE_COUNT):
        d = [r["zone_min"][z + 1] - r["zone_min"][z] for r in rows if z + 1 in r["zone_min"]]
        if d:
            stay[z] = (statistics.median(d), len(d))
    reach = {z: statistics.median([r["zone_min"][z] for r in rows if z in r["zone_min"]])
             for z in range(1, SP.ZONE_COUNT + 1) if any(z in r["zone_min"] for r in rows)}
    return stay, reach


def report(stay, reach, seeds, wall):
    out, outside, walls = [], [], {}
    for z in range(Z_FROM, Z_TO + 1):
        if z not in stay:
            outside.append(z); out.append((z, None, target(z), None, len(seeds) and 0)); continue
        m, n = stay[z]; ratio = m / target(z)
        bad = abs(math.log(ratio)) > math.log(1 + TOL)
        if bad: outside.append(z)
        out.append((z, m, target(z), ratio, n))
    if wall:
        for z in range(SP.WALL_START, Z_TO + 1, SP.WALL_EVERY):
            nb = [stay[k][0] for k in (z - 1, z + 1) if k in stay]
            if z in stay and nb:
                walls[z] = stay[z][0] / (sum(nb) / len(nb))
    return out, outside, walls


def main(argv):
    global WALL_ON
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--no-wall", action="store_true")
    ap.add_argument("--max-min", type=int, default=900)
    ap.add_argument("--out", default=None)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--rw", type=float, default=None, help="보상 성장률을 잠시 바꿔 잰다 (격자용). 게임 파일은 안 건드린다")
    ap.add_argument("--no-new-weapons", action="store_true", help="M2 무기(unlock 있는 것)를 빼고 잰다 — 예측 M2-B3 의 '무기 넣기 전' 곡선")
    a = ap.parse_args(argv)
    if a.no_new_weapons:
        SP.WEAPON_TYPES[:] = [w for w in SP.WEAPON_TYPES if not w.get("unlock")]

    if a.selftest:
        # R003: 이 검사가 떨어질 수 있는가. 보상 성장을 1.20 으로 낮추면 뒤 구역이 곡선 밖으로 나가야 한다.
        keep = SP.ZONE_RW_G; SP.ZONE_RW_G = 1.20
        WALL_ON = False
        try:
            stay, reach = measure(list(range(1, 6)), wall=False, max_min=600)
        finally:
            SP.ZONE_RW_G = keep
        _, outside, _ = report(stay, reach, list(range(1, 6)), False)
        ok = len(outside) >= 6
        print("자가진단: 보상 성장 1.20 으로 낮추니 곡선 밖 구역 %d개 (6 이상이어야 검사가 살아 있다) → %s" % (len(outside), "통과" if ok else "실패"))
        return 0 if ok else 1

    assert not SP.drift(), "포트가 게임과 어긋났다 — 먼저 맞춰라"
    seeds = list(range(1, a.seeds + 1))
    if a.rw:
        SP.ZONE_RW_G = a.rw
    WALL_ON = not a.no_wall
    stay, reach = measure(seeds, wall=not a.no_wall, max_min=a.max_min)
    rows, outside, walls = report(stay, reach, seeds, not a.no_wall)
    print("목표 체류(z) = %.1f x %.2f^z 분 · 허용 ±%d%% · 구역 %d~%d · %d시드 · 벽 %s" % (TARGET_BASE, TARGET_G, TOL * 100, Z_FROM, Z_TO, len(seeds), "켬" if not a.no_wall else "끔"))
    print("구역 | 체류(중앙) | 목표 | 비율 | 시드")
    for z, m, t, r, n in rows:
        flag = "" if (r is not None and abs(math.log(r)) <= math.log(1 + TOL)) else "  ← 밖"
        print("%4d | %7s | %5.1f | %5s | %d%s" % (z, ("%.1f" % m) if m is not None else "-", t, ("%.2f" % r) if r is not None else "-", n, flag))
    trough = {}
    if walls:
        print("벽 구역 체류 / 이웃 평균:", {z: round(v, 2) for z, v in walls.items()}, "(M2-B2‴: 1.7~2.5)")
        trough = {z: round(stay[z + 1][0] / stay[z - 1][0], 2) for z in walls if z + 1 in stay and z - 1 in stay and stay[z - 1][0] > 0}
        print("벽 다음 구역 / 벽 앞 구역 (골짜기):", trough, "(M2-B2‴: 0.5 이상)")
    arr = {z: ((reach[z] - reach[CURVE_FROM]) / target_arrive(z)) for z in range(CURVE_FROM + 1, SP.ZONE_COUNT + 1) if z in reach and CURVE_FROM in reach}
    arr_out = [z for z, r in arr.items() if abs(math.log(r)) > math.log(1 + ARRIVE_TOL)]
    print("도달 시각 / 목표 누적 (구역 10~30):", {z: round(r, 2) for z, r in arr.items()}, "· ±%d%% 밖 %d개 %s (M2-B1‴: 3개 이하, 구역 10 기준 상대)" % (ARRIVE_TOL * 100, len(arr_out), arr_out))
    print("곡선 밖: %d개 %s · 30 도달(중앙) %s분" % (len(outside), outside, ("%.1f" % reach[30]) if 30 in reach else "-"))
    if a.out:
        json.dump({"측정일": datetime.date.today().isoformat(), "도구": "tools/curve_check.py", "시드": seeds, "벽": not a.no_wall, "새무기": not a.no_new_weapons,
                   "목표": "%.1f x %.2f^z" % (TARGET_BASE, TARGET_G), "허용": TOL, "구간": [Z_FROM, Z_TO],
                   "구역별": {str(z): {"체류": round(m, 3) if m is not None else None, "목표": round(t, 3), "비율": round(r, 4) if r is not None else None} for z, m, t, r, n in rows},
                   "곡선밖": outside, "벽비": {str(z): round(v, 4) for z, v in walls.items()}, "골짜기": {str(z): v for z, v in trough.items()},
                   "도달비": {str(z): round(r, 4) for z, r in arr.items()}, "도달_밖": arr_out, "보상성장_사용": SP.ZONE_RW_G, "빌드도장": __import__("hashlib").sha256(open(SP.GAME, "rb").read()).hexdigest()[:16],
                   "도달_중앙_분": {str(z): round(v, 2) for z, v in reach.items()},
                   "판정하지_않는다": "M2-B1/B2 판정은 검증자·사람 몫이다. 여기는 만든 쪽의 측정이다."},
                  io.open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print("기록:", a.out)
    return min(len(outside), 200)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
