# -*- coding: utf-8 -*-
"""M10-P3 — 환생 한 번 뒤 두 번째 판이 얼마나 빨라지는가 (M10 3.2, 지시 #155 9).

거울(tools/sim_port.py)의 auto_run 으로 첫 판을 구역 30 까지 → 게임과 같은 doRebirth(훈장 floor((최고구역−9)^1.5))
→ 같은 Sim 을 이어 두 번째 판을 구역 30 까지. 장비·설계도·입수 레벨은 남고 구역·부품·능력치 레벨은 처음으로(게임과 같다).
예측 M10-P3: 두 번째 판의 30구역 도달이 첫 판의 50% 이하. 50% 를 넘으면 틀렸다 — 훈장 효과(MEDAL_PER)를 올린다.
쓰는 법: python3 tools/rebirth_check.py [--seeds 8] [--out measurements/rebirth-M10-....json]
종료 코드: 비율 중앙이 0.5 를 넘으면 1."""
import os, sys, json, argparse, statistics, datetime
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim_port as SP

MAX_MIN = 600


def one(seed):
    r1 = SP.auto_run(seed=seed, max_min=MAX_MIN)
    s = r1["sim"]; first = r1["zone_min"].get(SP.ZONE_COUNT)
    best = s.G.get("bestZone") or s.G["zone"]
    gain = s.doRebirth()
    r2 = SP.auto_run(seed=seed, max_min=MAX_MIN, sim=s)
    second = r2["zone_min"].get(SP.ZONE_COUNT)
    return dict(seed=seed, first_min=first, best=best, medals=gain, second_min=second,
                ratio=(second / first) if first and second else None, z10_second=r2["zone_min"].get(10))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--seeds", type=int, default=8); ap.add_argument("--out")
    a = ap.parse_args()
    with Pool(min(8, os.cpu_count() or 1)) as p:
        rows = p.map(one, range(1, a.seeds + 1))
    for r in rows:
        print("시드 %d: 첫 판 %s분 (최고 %d, 훈장 +%d) → 두 번째 판 %s분 · 비율 %s"
              % (r["seed"], r["first_min"], r["best"], r["medals"], r["second_min"], ("%.2f" % r["ratio"]) if r["ratio"] else "-"))
    rs = [r["ratio"] for r in rows if r["ratio"]]
    med = statistics.median(rs) if rs else None
    print("비율 중앙 %s (M10-P3: 0.5 이하)" % (("%.2f" % med) if med is not None else "-"))
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump({"측정일": datetime.date.today().isoformat(), "도구": "tools/rebirth_check.py", "시드": a.seeds,
                       "행": rows, "비율중앙": med}, f, ensure_ascii=False, indent=1)
        print("기록:", a.out)
    return 1 if med is None or med > 0.5 else 0


if __name__ == "__main__":
    sys.exit(main())
