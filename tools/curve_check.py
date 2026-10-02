# -*- coding: utf-8 -*-
"""목표 체류 곡선 대 실제 체류 — WBS-M3 1.1.

곡선은 **정본에서 읽는다** (`canon/10-scope.md` 의 기계가 읽는 값):
체류(z) = `SCOPE_STAY_T0_MIN` x `SCOPE_STAY_G`^(z-1), 적용 시작은 `SCOPE_STAY_FROM_ZONE`. 벽 구역은 x2.
**숫자를 이 파일에 적지 않는다.** c2 의 교훈이다 — "숫자를 여기 적지 않는다. 18차·M2 에서 두 번 낡았다".
2026-09-14 정본 개정: 0.6분 x 1.12^(z-1), 구역 1~30 전 구간 (지시 #84).
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

def _canon(name, cast=float):
    """정본의 `기계가 읽는 값` 에서 하나 읽는다. 없으면 죽는다 — 조용히 기본값을 쓰지 않는다."""
    import re
    txt = io.open(os.path.join(ROOT, "canon", "10-scope.md"), encoding="utf-8").read()
    m = re.search(r"^\s*%s\s*=\s*([0-9.]+)\s*$" % re.escape(name), txt, re.M)
    if not m:
        raise SystemExit("canon/10-scope.md 에 %s 가 없다 — 정본을 먼저 고쳐라" % name)
    return cast(m.group(1))


TARGET_BASE = _canon("SCOPE_STAY_T0_MIN")          # 0.6분 (정본)
TARGET_G    = _canon("SCOPE_STAY_G")               # 1.12  (정본)
CURVE_FROM  = _canon("SCOPE_STAY_FROM_ZONE", int)  # 1     (정본)
TOL = 0.20             # M3-B1 의 반증선 (±20%). 예측이 바뀌면 여기를 바꾼다
ARRIVE_TOL = 0.20      # 도달 시각은 정보로 같이 찍는다
WALL_MULT_TARGET = 2.0   # 지시 #63: 벽 ×2
WALL_START_TARGET = 10   # 벽은 구역 10 부터 (정본 표)
Z_FROM, Z_TO = CURVE_FROM, SP.ZONE_COUNT - 1   # 마지막 구역은 다음 구역이 없어 체류를 못 잰다 (M11: 60)


WALL_ON = True     # --no-wall 이면 False. 벽을 끄고 재면 목표에서도 벽을 뺀다 (22차 감사 지적)


def target(z):
    """정본: 0.6분 × 1.12^(z-1). 벽 구역은 ×2."""
    return TARGET_BASE * TARGET_G ** (z - 1) * (WALL_MULT_TARGET if (WALL_ON and z >= WALL_START_TARGET and z % 5 == 0) else 1)


def target_arrive(z):
    """곡선 시작 구역 도달을 0 으로 놓은 목표 누적."""
    return sum(target(k) for k in range(CURVE_FROM, z))


END_PARTS, DEATHS = None, None


def measure(seeds, wall=True, max_min=900):
    # 2026-09-18 병렬(지시 #130): 벽 끄기는 자식 안에서 (overrides)
    rows = SP.run_many(seeds, kw={"max_min": max_min}, overrides=({"WALL_KILL_MULT": 1} if not wall else None))
    stay = {}
    for z in range(1, SP.ZONE_COUNT):
        d = [r["zone_min"][z + 1] - r["zone_min"][z] for r in rows if z + 1 in r["zone_min"]]
        if d:
            stay[z] = (statistics.median(d), len(d))
    reach = {z: statistics.median([r["zone_min"][z] for r in rows if z in r["zone_min"]])
             for z in range(1, SP.ZONE_COUNT + 1) if any(z in r["zone_min"] for r in rows)}
    global END_PARTS, DEATHS
    END_PARTS = round(statistics.median([r["G"]["parts"] for r in rows]), 1)   # M6 5.2 / M6-B2 — 끝 시점 부품 잔액
    DEATHS = statistics.median([r["deaths"] for r in rows])
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
    print("목표 체류(z) = %.2f x %.2f^(z-1) 분 [정본] · 허용 ±%d%% · 구역 %d~%d · %d시드 · 벽 %s"
          % (TARGET_BASE, TARGET_G, TOL * 100, Z_FROM, Z_TO, len(seeds), "켬" if not a.no_wall else "끔"))
    print("구역 | 체류(중앙) | 목표 | 비율 | 시드")
    for z, m, t, r, n in rows:
        flag = "" if (r is not None and abs(math.log(r)) <= math.log(1 + TOL)) else "  ← 밖"
        print("%4d | %7s | %5.1f | %5s | %d%s" % (z, ("%.1f" % m) if m is not None else "-", t, ("%.2f" % r) if r is not None else "-", n, flag))
    trough = {}
    if walls:
        print("벽 구역 체류 / 이웃 평균:", {z: round(v, 2) for z, v in walls.items()}, "(M2-B2‴: 1.7~2.5)")
        trough = {z: round(stay[z + 1][0] / stay[z - 1][0], 2) for z in walls if z + 1 in stay and z - 1 in stay and stay[z - 1][0] > 0}
        print("벽 다음 구역 / 벽 앞 구역 (골짜기):", trough, "(M2-B2‴: 0.5 이상)")
    arr = {z: ((reach[z] - reach[CURVE_FROM]) / target_arrive(z)) for z in range(CURVE_FROM + 1, SP.ZONE_COUNT + 1) if z in reach and CURVE_FROM in reach and target_arrive(z) > 0}
    arr_out = [z for z, r in arr.items() if abs(math.log(r)) > math.log(1 + ARRIVE_TOL)]
    print("도달 시각 / 목표 누적 (정보):", {z: round(r, 2) for z, r in arr.items()}, "· ±%d%% 밖 %d개 %s (M2-B1‴: 3개 이하, 구역 10 기준 상대)" % (ARRIVE_TOL * 100, len(arr_out), arr_out))
    ZL = SP.ZONE_COUNT
    print("곡선 밖: %d개 %s · %d 도달(중앙) %s분" % (len(outside), outside, ZL, ("%.1f" % reach[ZL]) if ZL in reach else "-"))
    if a.out:
        json.dump({"측정일": datetime.date.today().isoformat(), "도구": "tools/curve_check.py", "시드": seeds, "벽": not a.no_wall, "새무기": not a.no_new_weapons,
                   "끝_부품_중앙": END_PARTS, "사망_중앙": DEATHS,     # M6 5.2 / M6-B2
                   "목표": "%.2f x %.2f^(z-1)" % (TARGET_BASE, TARGET_G), "목표_출처": "canon/10-scope.md", "허용": TOL, "구간": [Z_FROM, Z_TO],
                   "구역별": {str(z): {"체류": round(m, 3) if m is not None else None, "목표": round(t, 3), "비율": round(r, 4) if r is not None else None} for z, m, t, r, n in rows},
                   "곡선밖": outside, "벽비": {str(z): round(v, 4) for z, v in walls.items()}, "골짜기": {str(z): v for z, v in trough.items()},
                   "도달비": {str(z): round(r, 4) for z, r in arr.items()}, "도달_밖": arr_out, "보상성장_사용": SP.ZONE_RW_G, "빌드도장": __import__("hashlib").sha256(open(SP.GAME, "rb").read()).hexdigest()[:16],
                   "도달_중앙_분": {str(z): round(v, 2) for z, v in reach.items()},
                   "판정하지_않는다": "M3-B1 판정은 검증자·사람 몫이다. 여기는 만든 쪽의 측정이다."},
                  io.open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print("기록:", a.out)
    return min(len(outside), 200)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
