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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim_port as S

LINE_MIN = 30.0          # 연속 30분 안에 셋 다 채워지면 실패


def measure(seeds):
    """각 시드에서 과제 셋이 need 에 **처음 닿은 시각**(분)을 잰다.

    `questProgress` 를 감싼다 — 매수 줄처럼 여기서 진행을 새로 짜면 자가 둘이 된다."""
    orig = S.Sim.questProgress
    rows = []
    try:
        for sd in seeds:
            hit = {}

            def qp(self, qid, n, _o=orig, _h=hit):
                _o(self, qid, n)
                if self.G["quest"].get(qid, 0) >= S.QUEST_NEEDS[qid] and qid not in _h:
                    _h[qid] = self.t / 60.0

            S.Sim.questProgress = qp
            S.auto_run(seed=sd, max_min=900)
            rows.append(dict(hit))
    finally:
        S.Sim.questProgress = orig        # 감싼 것은 반드시 벗긴다
    return rows


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--out")
    a = ap.parse_args(argv[1:])
    seeds = list(range(1, a.seeds + 1))

    rows = measure(seeds)
    full = [r for r in rows if len(r) == len(S.QUEST_DEFS_IDS)]
    last = sorted(max(r.values()) for r in full)
    within = [x for x in last if x <= LINE_MIN]

    print("과제: %s (need %s)" % (S.QUEST_DEFS_IDS, [S.QUEST_NEEDS[q] for q in S.QUEST_DEFS_IDS]))
    print("셋 다 채워진 시드: %d/%d" % (len(full), len(seeds)))
    if last:
        print("마지막 하나가 채워진 시각(분): 중앙 %.2f · 최소 %.2f · 최대 %.2f"
              % (statistics.median(last), last[0], last[-1]))
    print("연속 %.0f분 안에 셋 다 채워진 시드: %d/%d" % (LINE_MIN, len(within), len(seeds)))
    ok = len(within) == 0
    print("완료 판정('채워지지 않는다'): %s" % ("통과" if ok else "**떨어진다**"))

    if a.out:
        stamp = hashlib.sha256(io.open(S.GAME, "rb").read()).hexdigest()[:16]
        rec = {"측정일": datetime.date.today().isoformat(),
               "대상": "일일 과제 3개가 연속 30분 안에 다 채워지는지 — M4 1.2 / 예측 M4-B1",
               "빌드도장": stamp, "도구": "tools/quest_pace.py", "시드": seeds,
               "과제": {q: S.QUEST_NEEDS[q] for q in S.QUEST_DEFS_IDS},
               "시드별_처음_닿은_시각_분": rows,
               "셋_다_채워진_시드": len(full),
               "마지막_완료_시각_분": {"중앙": round(statistics.median(last), 2) if last else None,
                                      "최소": round(last[0], 2) if last else None,
                                      "최대": round(last[-1], 2) if last else None},
               "선_분": LINE_MIN,
               "선_안에_들어온_시드": len(within),
               "결과": "통과" if ok else "떨어진다",
               "내가_틀린_것": "2026-09-15 에 나는 '못 잰다'고 적었다. 판정 문구가 재라는 것은 수령이 아니라 채워지는 시각이고, questProgress 가 이미 세고 있었다. 29차 감사가 잡았다.",
               "판정하지_않는다": "M4-B1 판정은 검증자·사람 몫이다."}
        io.open(a.out, "w", encoding="utf-8").write(json.dumps(rec, ensure_ascii=False, indent=2))
        print("기록: %s" % a.out)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
