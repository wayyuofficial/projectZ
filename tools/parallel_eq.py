# -*- coding: utf-8 -*-
"""병렬(run_many)과 순차(auto_run)가 **같은 결과**를 내는지 — 자를 본다.

2026-09-18 지시 #130: 배터리를 병렬로 바꿨다. 시드마다 독립이라 같아야 하지만, "같아야 한다" 는 말이 아니라 실행으로 보인다.
기준·축 잠금·벽 끄기·집중 사격·과제 감싸기·매수 콜백 여섯 경로를 시드 몇 개로 돌려 zone_min/total_min/idle/hits/buys 를 대조한다.
    python tools/parallel_eq.py --seeds 3 --out measurements/parallel-eq-YYYY-MM-DD.json
"""
import sys, os, io, json, argparse, hashlib, datetime, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import sim_port as S


def one(name, seeds, **opt):
    t0 = time.time(); par = S.run_many(seeds, **opt); t1 = time.time()
    seq = S.run_many(seeds, workers=1, **opt); t2 = time.time()
    keys = ("zone_min", "total_min", "final_zone", "deaths", "idle_buy", "quest_hits")
    same = all(a[k] == b[k] for a, b in zip(par, seq) for k in keys) and \
           all([tuple(x) for x in a["buys"]] == [tuple(x) for x in b["buys"]] for a, b in zip(par, seq)) and \
           all(abs(a["income"].get("sell", 0) - b["income"].get("sell", 0)) < 1e-6 for a, b in zip(par, seq))
    return {"경로": name, "같다": same, "병렬_초": round(t1 - t0, 1), "순차_초": round(t2 - t1, 1),
            "예": {"total_min": [r["total_min"] for r in seq], "final_zone": [r["final_zone"] for r in seq]}}


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--max-min", type=int, default=200)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    seeds = list(range(1, a.seeds + 1)); kw = {"max_min": a.max_min}
    rows = [one("기준", seeds, kw=kw),
            one("축 잠금(atk)", seeds, kw=kw, lock_stat="atk"),
            one("벽 끄기", seeds, kw=kw, overrides={"WALL_KILL_MULT": 1}),
            one("집중 사격", seeds, kw=dict(kw, focus_duty=(3.0, 48.0))),
            one("과제 감싸기", seeds, kw=kw, want_quest=True),
            one("매수 콜백", seeds, kw=kw, want_buys=True)]
    stamp = hashlib.sha256(io.open(os.path.join(ROOT, "game", "index.html"), "rb").read()).hexdigest()[:16]
    ok = all(r["같다"] for r in rows)
    for r in rows:
        print("%-10s %s  병렬 %.1fs · 순차 %.1fs" % (r["경로"], "같다" if r["같다"] else "**다르다**", r["병렬_초"], r["순차_초"]))
    print("결과:", "전부 같다" if ok else "**어긋남**")
    if a.out:
        rec = {"측정일": datetime.date.today().isoformat(), "대상": "병렬 run_many 와 순차 auto_run 의 결과 일치 (지시 #130)", "빌드도장": stamp,
               "도구": "tools/parallel_eq.py", "시드": seeds, "상한_분": a.max_min, "cpu": os.cpu_count(), "경로": rows, "전부_같다": ok}
        io.open(os.path.join(ROOT, a.out), "w", encoding="utf-8").write(json.dumps(rec, ensure_ascii=False, indent=2))
        print("기록:", a.out)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
