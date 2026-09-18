# -*- coding: utf-8 -*-
"""능력치 축이 **실제로 쓸모 있는가** — 그 축을 잠그고 돌려 진행이 얼마나 나빠지는지.

왜 만들었나 (2026-09-14, M3 3.2):
`upgrade_cadence` 의 **부품 배분**으로 재려 했더니 다섯 축이 전부 18~19% 로 나왔다.
그런데 그건 축이 쓸모 있어서가 아니라 **매수 정책이 "가장 싼 것부터" 라 골고루 사서**다.
정책이 쓸모를 안 보므로 배분은 쓸모를 못 잰다 — 판정의 주어와 표본이 어긋난다 (R004).

이 도구는 다르게 잰다: **축 하나를 레벨 0 에 묶어 두고** 같은 시드를 돌려
구역 30 도달 시각이 얼마나 늦어지는지 본다. 안 늦어지면 그 축은 없어도 되는 축이다.

  python tools/axis_value.py --seeds 8
  python tools/axis_value.py --seeds 20 --out measurements/axis-value-YYYY-MM-DD.json

## 못 보는 것 (숨기지 않는다)
- 여전히 `auto_run` 의 정책 안에서 잰다. 사람은 다르게 살 수 있다.
- 축을 잠그면 그 부품이 **다른 축으로 흘러간다.** 그래서 "이 축이 없으면 얼마나 손해인가" 가 아니라
  "이 축에 쓸 돈을 다른 데 써도 되는가" 를 재는 것이다. 그게 사람이 실기에서 말한 것과 같은 질문이다.
- **판정이 아니다.** `M3-B3` 의 판정은 사람이 한다.
"""
import io, os, sys, json, argparse, statistics, hashlib, datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import sim_port as SP

LOCKED = 1e18          # 이 비용이면 절대 못 산다 = 레벨 0 에 묶인다


def run_once(seeds, lock=None, max_min=400):   # 2026-09-18: 900 → 400. 잠근 축은 완주를 못 해 상한까지 돈다 — 8구성×20시드×900분이면 한 시간 넘게 걸렸다(지시 #128)
    keep = {s["id"]: s["cost0"] for s in SP.STATS}
    if lock:
        for s in SP.STATS:
            if s["id"] == lock:
                s["cost0"] = LOCKED
    try:
        rows = [SP.auto_run(seed=sd, max_min=max_min) for sd in seeds]
    finally:
        for s in SP.STATS:
            s["cost0"] = keep[s["id"]]
    reach = [r["zone_min"].get(SP.ZONE_COUNT) for r in rows]
    done = [x for x in reach if x is not None]
    return (statistics.median(done) if done else None,
            len(done), statistics.median([r["deaths"] for r in rows]),
            statistics.median([r["final_zone"] for r in rows]))


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=8)
    ap.add_argument("--out")
    # M4 4.3 재현용 (2026-09-16, 사례 23). 여기 든 축은 buyStat 이 거부한다 = 장비로만 오른다.
    # 2026-09-15 실험은 일회용 스크립트였고, 그때 auto_run 이 이 축을 후보에서 안 빼서
    # "진행이 통째로 막혔다" 가 나왔다. 저장소 스크립트로 재현 가능하게 여기 둔다 (R005 1항).
    ap.add_argument("--gear-only", default="", help="쉼표로 나눈 축 id — 장비 전용으로 두고 잰다 (예: hp,reg)")
    ap.add_argument("--max-min", type=int, default=400, help="한 런의 상한(시뮬 분). 잠근 축은 완주를 못 하므로 여기까지만 돈다 — 기준(구역 30 도달 중앙)의 3배면 '느려짐' 판정에 충분하다")
    a = ap.parse_args(argv[1:])
    seeds = list(range(1, a.seeds + 1))
    gear_only = {x.strip() for x in a.gear_only.split(",") if x.strip()}
    # 2026-09-17: 원본이 gearOnly 를 갖게 됐다(4.3 (a)). 옵션 없이도 원본 것은 잠금 대상이 아니다 —
    # 못 사는 축을 잠가 봐야 0% 가 나와 "없어도 되는 축" 으로 잘못 찍힌다 (같은 날 실제로 그랬다).
    gear_only |= set(SP.GEAR_ONLY_STATS)
    SP.GEAR_ONLY_STATS = set(gear_only)
    if gear_only:
        print("장비 전용 축: %s (능력치 탭에서 못 산다)" % sorted(gear_only))

    base, bn, bd, bz = run_once(seeds, max_min=a.max_min)
    print("기준(전부 사용) : 구역 30 도달 %s · 완주 %d/%d · 사망 %.0f회"
          % (("%.1f분" % base) if base else "못함", bn, len(seeds), bd))
    rows, dead = [], []
    for s in SP.STATS:
        if s["id"] in gear_only:
            rows.append({"축": s["id"], "이름": s["name"], "장비_전용": True})
            print("%-4s %-8s 장비 전용 — 잠금 대상 아님" % (s["id"], s["name"]))
            continue
        m, n, d, z = run_once(seeds, lock=s["id"], max_min=a.max_min)
        if base and m:
            delta = (m - base) / base * 100
        else:
            delta = None
        rows.append({"축": s["id"], "이름": s["name"], "잠갔을때_도달분": round(m, 1) if m else None,
                     "완주": "%d/%d" % (n, len(seeds)), "느려짐_퍼센트": round(delta, 1) if delta is not None else None,
                     "사망": d, "도달구역중앙": z})
        tag = ""
        if delta is not None and delta < 5:
            dead.append(s["id"]); tag = "  ← 없어도 되는 축"
        elif m is None:
            tag = "  ← 이 축이 없으면 못 깬다"
        print("%-4s %-8s 잠금 → 도달 %8s · 완주 %s · 느려짐 %7s · 사망 %.0f%s"
              % (s["id"], s["name"], ("%.1f분" % m) if m else "못함", "%d/%d" % (n, len(seeds)),
                 ("%+.1f%%" % delta) if delta is not None else "-", d, tag))
    print()
    print("없어도 되는 축(느려짐 5%% 미만): %d개 %s" % (len(dead), dead))
    if a.out:
        stamp = hashlib.sha256(open(SP.GAME, "rb").read()).hexdigest()[:16]
        io.open(a.out, "w", encoding="utf-8").write(json.dumps(
            {"측정일": datetime.date.today().isoformat(), "도구": "tools/axis_value.py", "시드": seeds,
             "빌드도장": stamp, "기준_도달분": round(base, 1) if base else None, "기준_사망": bd,
             "축별": rows, "없어도_되는_축": dead,
             "판정하지_않는다": "M3-B3 판정은 사람 몫이다. 여기는 만든 쪽의 측정이다."},
            ensure_ascii=False, indent=2))
        print("기록:", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
