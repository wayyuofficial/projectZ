# -*- coding: utf-8 -*-
"""장비 판매가 부품 수입의 몇 퍼센트인지 — M4 4.1 / 예측 M4-B3.

조사에서 가장 많이 언급된 루프가 *장비를 쏟아내고 안 쓰는 것을 파는 것*이다.
그 루프가 살아 있으려면 판매가 수입에서 **무시 못 할 몫**이어야 한다. M4 계획의 선은 **30% 이상**.

`auto_run` 이 돌려주는 `sim.income`(측정용 계수기 — 원본에 없다) 을 읽는다.
매수·판매 줄을 여기서 새로 짜지 않는다 — 자가 둘이 되면 갈라진다 (cases/2026-09-16-22).

**이 파일이 있는 이유**: 2026-09-15 측정은 일회용 스크립트였고, 그 기록(`gear-sell-share-2026-09-15.json`)은
WBS 가 인용하지 않아 `c19` 가 낡은 줄도 몰랐다. 29차 감사가 잡았다 — WBS 4.1 행이 그 옛 값
("구역 30 도달 180.9분")을 현재인 양 들고 있었다.

쓰는 법:
    python tools/sell_share.py --seeds 20 --out measurements/sell-share-YYYY-MM-DD.json
"""
import io, os, sys, json, argparse, hashlib, datetime, statistics

sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # cp949 콘솔에서 '—' 로 죽어 기록을 못 남겼다 (30차 감사)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim_port as S

LINE = 15.0   # 2026-09-30 지시 #132(위임): 30 → 15. 뽑기가 '조금씩' 이 되면서 파는 것도 준다 — plans/결정요청-M6-5단계-2026-09-18.md 1절


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--out")
    a = ap.parse_args(argv[1:])
    seeds = list(range(1, a.seeds + 1))

    kill = sell = 0.0
    mins, done, idle = [], 0, 0
    for r in S.run_many(seeds, kw={"max_min": 900}):   # 2026-09-18 병렬(지시 #130)
        inc = r["income"] or {}
        kill += inc.get("kill", 0.0)
        sell += inc.get("sell", 0.0)
        idle += r["idle_buy"]
        if r["final_zone"] >= S.ZONE_COUNT:
            done += 1
            mins.append(r["total_min"])
    pct = sell / (kill + sell) * 100.0 if (kill + sell) else 0.0
    ok = pct >= LINE

    print("시드 %d · 완주 %d/%d · 구역 30 도달(중앙) %s분 · 헛돈틱 %d"
          % (len(seeds), done, len(seeds), ("%.1f" % statistics.median(mins)) if mins else "-", idle))
    print("처치 수입 %.0f · 판매 수입 %.0f" % (kill, sell))
    print("판매 비중 %.1f%% (선 %.0f%% 이상) — %s" % (pct, LINE, "안쪽" if ok else "**미달**"))

    if a.out:
        stamp = hashlib.sha256(io.open(S.GAME, "rb").read()).hexdigest()[:16]
        rec = {"측정일": datetime.date.today().isoformat(),
               "대상": "판매가 부품 수입의 몇 퍼센트인지 — M4 4.1 / M4-B3",
               "빌드도장": stamp, "도구": "tools/sell_share.py", "시드": seeds,
               "완주": "%d/%d" % (done, len(seeds)),
               "구역30_도달_중앙_분": round(statistics.median(mins), 1) if mins else None,
               "처치_수입": round(kill, 2), "판매_수입": round(sell, 2),
               "판매_비중_퍼센트": round(pct, 1), "선": "%.0f%% 이상" % LINE,
               "헛돈틱": idle, "결과": "통과" if ok else "미달",
               "판정하지_않는다": "M4-B3 판정은 검증자·사람 몫이다."}
        io.open(a.out, "w", encoding="utf-8").write(json.dumps(rec, ensure_ascii=False, indent=2))
        print("기록: %s" % a.out)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
