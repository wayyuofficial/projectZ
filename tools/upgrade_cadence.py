# -*- coding: utf-8 -*-
"""업그레이드가 얼마나 자주 일어나는가 — 구역별 횟수와 간격.

사람이 실기에서 말한 것: *"초반 30구역 업그레이드가 너무 오래 걸린다."* (2026-09-11)
목표 **체류** 곡선은 그 느낌을 못 잰다. 체류가 짧아도 그 안에서 아무것도 안 올라가면 느리게 느껴진다.
이 도구는 **무엇을 언제 샀는지**를 세서 그 느낌에 숫자를 붙인다.

`sim_port.auto_run` 의 `on_buy` 를 쓴다 — 매수 정책은 `curve_check` 와 **같은 루프**다. 여기서 따로 만들지 않는다.

쓰는 법:
    python tools/upgrade_cadence.py --seeds 20 --out measurements/upgrade-cadence-YYYY-MM-DD.json
"""
import io, os, sys, json, argparse, hashlib, datetime, statistics

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim_port as S


def measure(seeds, max_min=900):
    per_zone = {}          # 구역 -> [간격(초), ...]
    counts = {}            # 구역 -> [시드별 매수 횟수]
    kinds = {"능력치": 0, "무기": 0}
    spend = {}             # 축 -> 쓴 부품 합 (M3 3.2 / M3-B3)
    for sd in seeds:
        buys = []
        S.auto_run(seed=sd, max_min=max_min, on_buy=lambda t, z, bid, c: buys.append((t, z, bid, c)))
        by_zone = {}
        for t, z, bid, cost in buys:
            by_zone.setdefault(z, []).append(t)
            kinds["무기" if bid.startswith("W:") else "능력치"] += 1
            key = "무기" if bid.startswith("W:") else bid
            spend[key] = spend.get(key, 0.0) + cost
        for z, ts in by_zone.items():
            counts.setdefault(z, []).append(len(ts))
            ts = sorted(ts)
            for i in range(1, len(ts)):
                per_zone.setdefault(z, []).append(ts[i] - ts[i - 1])
    return per_zone, counts, kinds, spend


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--out")
    a = ap.parse_args(argv[1:])
    seeds = list(range(1, a.seeds + 1))

    per_zone, counts, kinds, spend = measure(seeds)
    zones = sorted(counts.keys())
    rows, thin = [], []
    for z in zones:
        n = statistics.median(counts[z])
        gaps = per_zone.get(z, [])
        gap = statistics.median(gaps) if gaps else None
        rows.append({"구역": z, "매수_횟수_중앙": n,
                     "간격_초_중앙": round(gap, 1) if gap is not None else None})
        if n < 3:
            thin.append(z)

    print("구역 | 매수 횟수(중앙) | 업그레이드 간격 초(중앙)")
    for r in rows:
        print("%4d | %13.1f | %s" % (r["구역"], r["매수_횟수_중앙"],
                                     ("%8.1f" % r["간격_초_중앙"]) if r["간격_초_중앙"] else "       -"))
    print()
    print("매수가 3회 미만인 구역: %d개 %s" % (len(thin), thin))
    print("산 것: 능력치 %d · 무기 %d" % (kinds["능력치"], kinds["무기"]))
    tot = sum(spend.values()) or 1.0
    share = {k: round(v / tot * 100, 1) for k, v in sorted(spend.items(), key=lambda x: -x[1])}
    print("부품 배분(%%): %s" % share)
    thin_axis = [k for k, v in share.items() if k != "무기" and v < 10.0]
    print("10%% 미만인 능력치 축: %d개 %s (M3-B3: 0개여야 한다)" % (len(thin_axis), thin_axis))

    if a.out:
        stamp = hashlib.sha256(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                 "..", "game", "index.html"), "rb").read()).hexdigest()[:16]
        rec = {"측정일": datetime.date.today().isoformat(), "도구": "tools/upgrade_cadence.py",
               "시드": seeds, "빌드도장": stamp, "구역별": rows,
               "매수_3회_미만_구역": thin, "산것": kinds,
               "부품_배분_퍼센트": share, "열퍼센트_미만_축": thin_axis,
               "판정하지_않는다": "여기는 만든 쪽의 측정이다. 판정은 검증자·사람 몫이다."}
        io.open(a.out, "w", encoding="utf-8").write(json.dumps(rec, ensure_ascii=False, indent=2))
        print("기록: %s" % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
