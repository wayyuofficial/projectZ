# -*- coding: utf-8 -*-
"""plans/balance-zones.csv 를 게임 상수에서 다시 만든다.

손으로 적지 않는다. `game/index.html` 의 상수를 읽어 계산한다.
2026-09-08: 8.1 에서 게임 상수를 재보정하고 이 표를 안 고쳐서 10개 구역이 전부 틀렸다.
표를 손으로 유지하면 또 갈라진다. 그래서 생성물로 바꿨다.

실행: python tools/gen_balance_csv.py
검사: checks/c13_balance_table.py 가 표와 게임 상수가 어긋나면 잡는다.
"""
import io, os, re, sys, math

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HEADER = "구역,좀비HP,좀비DPS,처치보상_부품,필요DPS_3초컷,필요공격레벨,누적업그레이드비용,처치수"

def hp_knot(t, z):
    """M15 — 게임 ZONE_HP_KNOTS(log 체력 오프셋 매듭)를 읽어 hpKnot(z) 와 같은 값을 낸다. 상수가 없으면 0(예전 곡선)."""
    m = re.search(r"const\s+ZONE_HP_KNOTS\s*=\s*\[(.*?)\n\];", t, re.S)
    if not m:
        return 0.0
    K = [[float(v) for v in re.findall(r"-?[\d.]+", r)] for r in re.findall(r"\[([^\[\]]*)\]", re.sub(r"//[^\n]*", "", m.group(1)))]
    if z <= K[0][0]:
        return K[0][1]
    for i in range(1, len(K)):
        if z <= K[i][0]:
            return K[i - 1][1] + (K[i][1] - K[i - 1][1]) * (z - K[i - 1][0]) / (K[i][0] - K[i - 1][0])
    return K[-1][1]


def read_consts(root):
    """게임 파일에서 곡선 상수를 읽는다. 못 읽으면 예외를 낸다 — 조용히 넘어가지 않는다."""
    p = os.path.join(root, "game", "index.html")
    with io.open(p, encoding="utf-8-sig", errors="replace") as f:
        t = f.read()

    def num(pattern):
        m = re.search(pattern, t)
        if not m:
            raise ValueError("게임 파일에서 못 찾음: " + pattern)
        return float(m.group(1))

    c = {
        "ZONE_HP0": num(r"const ZONE_HP0\s*=\s*([\d.]+)"),
        "ZONE_HP_G": num(r"ZONE_HP_G\s*=\s*([\d.]+)"),
        "ZONE_RW0": num(r"const ZONE_RW0\s*=\s*([\d.]+)"),
        "ZONE_RW_G": num(r"ZONE_RW_G\s*=\s*([\d.]+)"),
        "DPS_RATIO": num(r"const ZOMBIE_DPS_RATIO\s*=\s*([\d.]+)"),
        "ZONES": int(num(r"const ZONE_COUNT\s*=\s*(\d+)")),
        "WALL_EVERY": int(num(r"const WALL_EVERY\s*=\s*(\d+)")),   # M2 벽 (처치 수)
        "WALL_KILLS": int(num(r"WALL_KILL_MULT\s*=\s*(\d+)")),
        "WALL_START": int(num(r"WALL_START\s*=\s*(\d+)")),
        "KILLS": int(num(r"const KILLS_PER_ZONE\s*=\s*(\d+)")),
    }
    c["KNOT"] = lambda z, _t=t: hp_knot(_t, z)   # M15 — 체력 곡선 모양
    m = re.search(r"\{\s*id:\s*'atk'.*?base:\s*([\d.]+).*?growth:\s*([\d.]+)"
                  r".*?cost0:\s*([\d.]+).*?costG:\s*([\d.]+)", t, re.S)
    if not m:
        raise ValueError("STATS 의 atk 항목을 못 찾음")
    c["ATK_BASE"], c["ATK_GROWTH"] = float(m.group(1)), float(m.group(2))
    c["ATK_COST0"], c["ATK_COSTG"] = float(m.group(3)), float(m.group(4))
    return c


def rows(c):
    out = []
    for z in range(1, c["ZONES"] + 1):
        hp = c["ZONE_HP0"] * c["ZONE_HP_G"] ** (z - 1) * math.exp(c["KNOT"](z))   # M15 — 게임 zoneHP 와 같은 식
        dps = hp * c["DPS_RATIO"]
        kills = c["KILLS"] * (c["WALL_KILLS"] if (z >= c["WALL_START"] and z % c["WALL_EVERY"] == 0) else 1)   # M2 벽 — 구역 10 부터
        rw = c["ZONE_RW0"] * c["ZONE_RW_G"] ** (z - 1) * c["KILLS"] / kills   # M2 벽: 처치당 보상 ÷3
        need = hp / 3.0
        lvl = math.log(need / c["ATK_BASE"]) / math.log(c["ATK_GROWTH"])
        lvl = max(0.0, lvl)
        g = c["ATK_COSTG"]
        cost = c["ATK_COST0"] * (g ** lvl - 1) / (g - 1)
        out.append((z, round(hp), round(dps), round(rw, 1), round(need), round(lvl), round(cost), kills))
    return out


def main():
    c = read_consts(ROOT)
    out = os.path.join(ROOT, "plans", "balance-zones.csv")
    with io.open(out, "w", encoding="utf-8-sig") as f:
        f.write(HEADER + "\n")
        for r in rows(c):
            f.write(",".join(str(x) for x in r) + "\n")
    print("생성: %s" % out)
    print("상수: " + " ".join("%s=%s" % (k, v) for k, v in sorted(c.items())))
    for r in rows(c):
        print("  구역%2d  HP %6d  보상 %6s  필요DPS %5d  누적비용 %d" % (r[0], r[1], r[3], r[4], r[6]))


if __name__ == "__main__":
    main()
