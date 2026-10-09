# -*- coding: utf-8 -*-
"""일일 과제 3개가 얼마나 빨리 다 채워지는지 — M4 1.2 / 예측 M4-B1.

계획의 뜻: *일일 과제를 한 번에 다 못 끝내게 해야 하루에 두 번 이상 앱을 켤 이유가 생긴다.*
완료 판정: **20시드 1런에서 과제 3개가 연속 30분 안에 전부 채워지지 않는다.**

## 이 파일이 있는 이유 — 나는 "못 잰다"고 적었다. 거짓이었다

2026-09-15 에 나는 WBS 에 *"시뮬은 과제를 수령하지 않아 못 잰다. 사람이 문구를 정해야 한다"* 고 적었다.
**틀렸다.** 판정 문구가 재라는 것은 *수령*이 아니라 **채워지는 시각**이고, 그건 `questProgress` 가
이미 세고 있다. 29차 감사가 이걸 잡았다 — 검증자는 15줄로 쟀고 **20/20 시드에서 떨어졌다.**

판정을 사람에게 넘기는 것과, **재보면 떨어질 것을 안 재고 넘기는 것**은 다르다.
뒤엣것은 R003 이 막으려는 바로 그것이다. 그래서 이 도구를 저장소에 박아 둔다.

쓰는 법:
    python tools/quest_pace.py --seeds 20 --out measurements/quest-pace-YYYY-MM-DD.json
"""
import io, os, sys, json, argparse, hashlib, datetime, statistics

sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # cp949 콘솔에서 '—' 로 죽어 기록을 못 남겼다 (30차 감사)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim_port as S

LINE_MIN = 30.0          # 연속 30분 안에 셋 다 채워지면 실패


def measure(seeds, start_hour=None):
    """각 시드에서 과제 셋이 need 에 **처음 닿은 시각**(분)을 잰다.

    `questProgress` 를 감싼다 — 매수 줄처럼 여기서 진행을 새로 짜면 자가 둘이 된다.
    `start_hour` 를 주면 그 시각(UTC, 포트 기준)에 런을 시작한다 — 시간대 셋을 각각 재려고 (30차 감사:
    "후보 문구조차 지금 도구로는 시간대 하나만 재진다")."""
    # 2026-09-18 병렬(지시 #130): 감싸기는 자식 프로세스 안에서(sim_port._worker want_quest) — 같은 감싸기, 자리만 옮겼다
    kw = {"max_min": 900}
    if start_hour is not None:
        kw["now_ms"] = S.DEFAULT_NOW_MS - (S.DEFAULT_NOW_MS % S.DAY_MS) + int(start_hour) * 3600000
    return [dict(r["quest_hits"]) for r in S.run_many(seeds, kw=kw, want_quest=True)]


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--out")
    ap.add_argument("--start-hour", type=int, default=None, help="런 시작 시각(UTC 0~23). 시간대 하나를 골라 잰다")
    a = ap.parse_args(argv[1:])
    seeds = list(range(1, a.seeds + 1))

    rows = measure(seeds, a.start_hour)
    # 지시 #187 — 일일 퀘스트가 고정 5개(시간대 없음)가 됐다. 처음 닿은 시각만 퀘스트별로 찍는다(광고 보기는 시뮬이 광고를 안 봐서 0).
    IDS = list(S.QUEST_DEFS_IDS)
    full = [r for r in rows if all(q in r for q in IDS if q != "ad")]
    last = sorted(max(v for k, v in r.items() if k != "ad") for r in full)
    within = [x for x in last if x <= LINE_MIN]
    print("일일 퀘스트: %s (need %s)" % (IDS, [S.QUEST_NEEDS[q] for q in IDS]))
    for qid in IDS:
        ts = sorted(r[qid] for r in rows if qid in r)
        print("  %-5s 채워진 시드 %d/%d%s" % (qid, len(ts), len(seeds), (" · 처음 닿은 시각(분) 중앙 %.2f · 최대 %.2f" % (statistics.median(ts), ts[-1])) if ts else ""))
    if last:
        print("광고 빼고 넷이 다 채워진 시각(분): 중앙 %.2f · 최소 %.2f · 최대 %.2f" % (statistics.median(last), last[0], last[-1]))
    bands, open_now, ok = {}, {}, len(within) == 0

    if a.out:
        stamp = hashlib.sha256(io.open(S.GAME, "rb").read()).hexdigest()[:16]
        rec = {"측정일": datetime.date.today().isoformat(),
               "대상": "일일 퀘스트(지시 #187 고정 5개)가 처음 채워지는 시각 — M4 1.2 / 예측 M4-B1 (옛 문구는 시간대 때 항등식, 지금은 플레이타임 30분이 있어 구조상 30분 전엔 다 못 채운다)",
               "빌드도장": stamp, "도구": "tools/quest_pace.py", "시드": seeds,
               "과제": {q: S.QUEST_NEEDS[q] for q in IDS},
               "시드별_처음_닿은_시각_분": rows,
               "넷_다_채워진_시드_광고제외": len(full),
               "시작_시각_옵션": a.start_hour,
               "과제별": {qid: {"채워진_시드": sum(1 for r in rows if qid in r),
                               "처음_닿은_시각_분_중앙": round(statistics.median([r[qid] for r in rows if qid in r]), 2) if any(qid in r for r in rows) else None}
                         for qid in IDS},
               "마지막_완료_시각_분": {"중앙": round(statistics.median(last), 2) if last else None,
                                      "최소": round(last[0], 2) if last else None,
                                      "최대": round(last[-1], 2) if last else None},
               "선_분": LINE_MIN,
               "선_안에_들어온_시드": len(within),
               "옛_문구_결과": ("항상 참 — 항등식, 판정 아님" if ok else "거짓"),
               "판정_문구": "없음 — 2026-09-17 (a) 뒤 옛 문구는 항등식. 새 문구는 사람이 정한다 (결정요청 1절 후보)",
               "내가_틀린_것": "2026-09-15 에 나는 '못 잰다'고 적었다. 판정 문구가 재라는 것은 수령이 아니라 채워지는 시각이고, questProgress 가 이미 세고 있었다. 29차 감사가 잡았다.",
               "판정하지_않는다": "M4-B1 판정은 검증자·사람 몫이다."}
        io.open(a.out, "w", encoding="utf-8").write(json.dumps(rec, ensure_ascii=False, indent=2))
        print("기록: %s" % a.out)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
