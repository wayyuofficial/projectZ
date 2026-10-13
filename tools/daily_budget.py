# -*- coding: utf-8 -*-
"""일일 보상 총량이 하루 예산 안인지 — M4 1.4.

방치형에서 일일 보상이 크면 **접속을 강제**한다. 정본이 아니라 M4 계획이 정한 선은
하루 총량이 **시간 수입의 20% 이하**다.

## 왜 다시 만들었나 — 앞의 측정은 항등식이었다

2026-09-15 측정은 브라우저에서 `dailyBudget() x 몫` 을 **다시 계산**해서 시간 수입과 나눴다.
지급이 전부 `dailyBudget()` 을 거치므로 그 비율은 **언제나** `DAILY_BUDGET x 몫합` 이다.
무엇을 고쳐도 17.1% 가 나온다 — **실패할 수 없는 시험**이다 (사례 12 와 같은 부류).

그래서 이 도구는 **실제로 받는다.** `rolloverDay` · `takeQuest` · `openSupply` 를 그대로 부르고,
**일부러 여러 번 시도한다.** 그러면 이런 것들이 잡힌다:

- 과제를 하루에 두 번 받을 수 있는가 (`questTaken` 가드가 실제로 서는가)
- 보급 상자가 `KEY_MAX` 를 넘어 열리는가
- 같은 날 `rolloverDay` 를 또 불러 접속 보상을 두 번 받는가
- 새 지급 경로가 `dailyBudget()` 을 안 거치는가 (첫 구현이 그래서 27~34% 였다)

쓰는 법:
    python tools/daily_budget.py --out measurements/daily-budget-YYYY-MM-DD.json
"""
import io, os, sys, json, argparse, hashlib, datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # cp949 콘솔에서 '—' 로 죽어 기록을 못 남겼다 (30차 감사)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim_port as S

LINE = 0.20             # 하루 총량 / 시간 수입
ZONES = (1, 5, 10, 15, 20, 25, 30)
SPAM = 5                # 일부러 여러 번 시도한다


def one_day(s):
    """하루치를 **실제로 받아** 합을 돌려준다. 일부러 과하게 시도한다."""
    got = 0.0
    before = s.G["parts"]
    r = s.rolloverDay()                       # 접속 보상
    for _ in range(SPAM):
        s.rolloverDay()                       # 같은 날 또 불러도 더 주면 안 된다
    for qid in S.QUEST_DEFS_IDS:              # 일일 퀘스트(지시 #187: 고정 5개) — 조건을 채우고 여러 번 받아 본다
        s.G["qd"][qid] = S.QUEST_NEEDS[qid]
        for _ in range(SPAM):
            s.takeQuest("d", qid)
    for _ in range(SPAM):
        s.takeQuest("da")                     # 일일 퀘스트 완료 — 부품은 없다(설계도·스킬북만)
    for _ in range(S.KEY_MAX + SPAM):         # 상자 — 열쇠보다 많이 눌러 본다
        s.openSupply()
    got = s.G["parts"] - before
    return got, (r or {}).get("day", 0)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    a = ap.parse_args(argv[1:])

    rows, worst = [], 0.0
    for z in ZONES:
        # **거기까지 실제로 플레이한 상태**에서 잰다. 구역만 바꾸고 능력치를 0 으로 두면
        # 구역 30 에서 좀비를 못 잡아 시간 수입이 구역 1 보다 작게 나온다 (2026-09-16 에 한 번 그랬다).
        # 매수 줄은 auto_run 의 것을 그대로 쓴다 — 여기서 새로 짜면 자가 둘이 된다.
        s = S.auto_run(seed=1, max_min=900, stop_zone=z)["sim"]
        hourly = s.partsPerSecondEstimate() * 3600
        # 접속 7일째(가장 큰 날)까지 밀어 놓고 그날 하루를 잰다 — **최악의 하루**를 본다
        for d in range(S.LOGIN_DAYS - 1):
            s.now_ms += S.DAY_MS
            s.rolloverDay()
        s.now_ms += S.DAY_MS
        s.G["parts"] = 0.0
        got, streak = one_day(s)
        pct = got / hourly * 100.0
        worst = max(worst, pct)
        rows.append({"구역": z, "시간수입": round(hourly), "일일총량": round(got),
                     "비율_퍼센트": round(pct, 1), "접속_연속일": streak})
        print("구역 %2d | 시간수입 %14.0f | 일일총량 %13.0f | %5.1f%% | 접속 %d일째"
              % (z, hourly, got, pct, streak))

    ok = worst <= LINE * 100 + 1e-9
    print("가장 큰 비율 %.1f%% (선 %.0f%%) — %s" % (worst, LINE * 100, "안쪽" if ok else "**넘었다**"))

    # 가드가 실제로 서는지 따로 말한다 — 위 숫자만 보면 왜 통과했는지 모른다
    s = S.Sim(seed=1); s.G["zone"] = 10; s.G["bestZone"] = 10; s.G["hp"] = s.maxHP()
    s.now_ms += S.DAY_MS; s.rolloverDay()
    q0 = S.QUEST_DEFS_IDS[0]                  # 지시 #187 — 첫 일일 퀘스트로 가드를 본다
    s.G["qd"][q0] = S.QUEST_NEEDS[q0]
    first = s.takeQuest("d", q0)
    second = s.takeQuest("d", q0)
    keys_used = 0
    s.G["keys"] = S.KEY_MAX
    for _ in range(S.KEY_MAX + SPAM):
        if s.openSupply() is not False:
            keys_used += 1
    guards = {"과제_두번째_수령": bool(second), "상자_연_횟수": keys_used, "열쇠_상한": S.KEY_MAX}
    print("가드: 과제 재수령 %s · 상자 %d회(상한 %d)"
          % ("**됨 — 새는 곳**" if second else "막힘", keys_used, S.KEY_MAX))
    ok = ok and not second and keys_used == S.KEY_MAX

    if a.out:
        stamp = hashlib.sha256(io.open(S.GAME, "rb").read()).hexdigest()[:16]
        rec = {"측정일": datetime.date.today().isoformat(),
               "대상": "일일 보상 총량이 하루 예산(시간 수입의 20%) 안인지 — M4 1.4",
               "빌드도장": stamp, "도구": "tools/daily_budget.py",
               "방법": "포트의 rolloverDay·takeQuest·openSupply 를 **실제로 불러** 받은 양을 센다. 일부러 %d번씩 더 눌러 중복 수령·열쇠 초과를 노린다. 접속 %d일째(가장 큰 날)를 잰다." % (SPAM, S.LOGIN_DAYS),
               "몫": {"일일 퀘스트(5개 각)": S.QUEST_DAILY_SHARE, "보급 상자": S.SUPPLY_SHARE,
                      "접속 최대": max(S.LOGIN_SHARES),
                      "합": round(S.QUEST_DAILY_SHARE * len(S.QUEST_DEFS_IDS) + S.SUPPLY_SHARE + max(S.LOGIN_SHARES), 3)},
               "구역별": rows, "가장_큰_비율_퍼센트": round(worst, 1), "선_퍼센트": LINE * 100,
               "가드": guards,
               "결과": "통과" if ok else "미달",
               "앞_측정의_결함": "2026-09-15 기록은 dailyBudget() x 몫 을 다시 계산한 것이라 비율이 늘 DAILY_BUDGET x 몫합 으로 나오는 **항등식**이었다. 이 도구는 실제로 받는다.",
               "처음엔_넘었다": "첫 구현은 과제 몫 합이 1.00 이라 하루 총량이 시간 수입의 27~34% 였다. 재보고 몫을 다시 나눴다.",
               "판정하지_않는다": "M4 판정은 검증자·사람 몫이다."}
        io.open(a.out, "w", encoding="utf-8").write(json.dumps(rec, ensure_ascii=False, indent=2))
        print("기록: %s" % a.out)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
