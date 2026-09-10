# -*- coding: utf-8 -*-
"""부스트 ON / OFF 두 시간대를 따로 잰다 — WBS-M2 5.1, 예측 M2-B4.

M1 21차 감사: 사람의 실측(구역 1→5 = 3분)은 광고 부스트를 켠 플레이에서만 재현됐고(포트 ON 3.27분),
밸런스 표·B1 은 부스트 없는 시간대(6.55분)였다. 같은 표가 두 값을 지지하는 것처럼 보였다.
그래서 기록에 두 열을 둔다. 사람 실측은 어느 열인지 적는다 (절차 60).

  python tools/boost_split.py --out measurements/balance-M2-boost-YYYY-MM-DD.json
"""
import io, os, sys, json, argparse, statistics, datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import sim_port as SP


def run(seeds, boost, max_min=900):
    keep = SP.Sim.boostActive
    if boost:
        SP.Sim.boostActive = lambda self: True     # 광고를 계속 본다 — 포트 안에서만
    try:
        rows = [SP.auto_run(seed=s, max_min=max_min) for s in seeds]
    finally:
        SP.Sim.boostActive = keep
    def med(z):
        v = [r["zone_min"][z] for r in rows if z in r["zone_min"]]
        return round(statistics.median(v), 2) if len(v) == len(seeds) else None
    return {str(z): med(z) for z in (5, 10, 15, 20, 25, 30)}


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=12)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    assert not SP.drift(), "포트가 게임과 어긋났다"
    seeds = list(range(1, a.seeds + 1))
    off = run(seeds, False); on = run(seeds, True)
    ratio = {z: round(on[z] / off[z], 3) for z in off if off[z] and on[z]}
    print("구역 | 부스트 OFF(분) | 부스트 ON(분) | ON/OFF")
    for z in off:
        print("%4s | %8s | %8s | %s" % (z, off[z], on[z], ratio.get(z)))
    inside = [z for z, r in ratio.items() if 0.5 <= r <= 0.7]
    print("ON/OFF 가 0.5~0.7 안인 구역: %d/%d (M2-B4)" % (len(inside), len(ratio)))
    if a.out:
        json.dump({"측정일": datetime.date.today().isoformat(), "도구": "tools/boost_split.py", "시드": seeds,
                   "부스트_OFF_도달_분": off, "부스트_ON_도달_분": on, "ON_OFF_비": ratio,
                   "사람_실측_시간대": "사람 실측은 measurements/device-*.json 에 어느 열인지 적는다. M1 지시 #45·#57 의 3분/2분은 부스트 ON 이다(21차 감사).",
                   "판정하지_않는다": "M2-B4 판정은 사람 몫이다."},
                  io.open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print("기록:", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
