# -*- coding: utf-8 -*-
"""집중 사격이 진행을 얼마나 바꾸는지 — M4 2.2 / 예측 M4-B2.

방치형에서 수동 개입은 **안 눌러도 되는** 것이어야 한다. 누르는 사람과 안 누르는 사람의
진행 차이가 크면 그건 방치형이 아니다. 정본이 정한 선은 **±5%** 다.

2026-09-15 에 한 번 이 자리에서 되돌렸다 — 지속 3초 · 배수 2 · 쿨 20초가 **−11.5%** 라
선을 넘었다. 배수 1.5 · 쿨 30초로 줄여 −4.5% 가 됐다.

**이 파일이 있는 이유**: 그때 측정은 일회용 스크립트였다. 빌드가 바뀔 때마다 다시 재야 하는데
(R005) 스크립트가 저장소에 없으면 그 값을 손으로 옮기게 된다 — 사례 17 이 그것이다.

쓰는 법:
    python tools/focus_check.py --seeds 20 --out measurements/focus-YYYY-MM-DD.json
"""
import io, os, sys, json, argparse, hashlib, datetime, statistics

sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # cp949 콘솔에서 '—' 로 죽어 기록을 못 남겼다 (30차 감사)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim_port as S


def run_set(seeds, duty):
    """duty=None 이면 안 누름. (켜는 초, 주기 초) 면 그만큼 누른다."""
    mins = []
    for sd in seeds:
        r = S.auto_run(seed=sd, max_min=900, focus_duty=duty)
        mins.append(r["total_min"])
    return statistics.median(mins)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--out")
    a = ap.parse_args(argv[1:])
    seeds = list(range(1, a.seeds + 1))

    sec, mult, cool = S.num("FOCUS_SEC"), S.num("FOCUS_MULT"), S.num("FOCUS_COOL_SEC")

    off = run_set(seeds, None)
    # 쿨타임을 지켜 누른다 — 사람이 가장 부지런했을 때
    on = run_set(seeds, (sec, cool))
    # 쿨타임을 무시한 극단. **상한**이지 사람이 낼 수 있는 값이 아니다
    always = run_set(seeds, (1.0, 1.0))

    d_on = (on - off) / off * 100.0
    d_always = (always - off) / off * 100.0

    print("설정: 지속 %.0f초 · 배수 %.2f · 쿨타임 %.0f초" % (sec, mult, cool))
    print("안 누름            : %.1f분" % off)
    print("쿨타임 지켜 누름   : %.1f분  (%+.1f%%)" % (on, d_on))
    print("늘 켬 (극단·상한)  : %.1f분  (%+.1f%%)" % (always, d_always))
    print("선: ±5%% — %s" % ("안쪽" if abs(d_on) <= 5.0 else "**넘었다**"))

    if a.out:
        stamp = hashlib.sha256(io.open(S.GAME, "rb").read()).hexdigest()[:16]
        rec = {"측정일": datetime.date.today().isoformat(),
               "대상": "집중 사격이 진행을 얼마나 바꾸는지 — M4 2.2",
               "빌드도장": stamp, "도구": "tools/focus_check.py", "시드": seeds,
               "설정": {"지속_초": sec, "배수": mult, "쿨타임_초": cool},
               "안누름_분": round(off, 1), "쿨타임_지켜_누름_분": round(on, 1),
               "차이_퍼센트": round(d_on, 1),
               "늘_켠_극단_분": round(always, 1), "늘_켠_차이_퍼센트": round(d_always, 1),
               "선": "±5%",
               "주의": "'늘 켬' 은 쿨타임을 무시한 극단이라 **상한**이다. 사람이 아무리 부지런해도 '쿨타임 지켜 누름' 을 못 넘는다.",
               "판정하지_않는다": "M4-B2 판정은 검증자·사람 몫이다."}
        io.open(a.out, "w", encoding="utf-8").write(json.dumps(rec, ensure_ascii=False, indent=2))
        print("기록: %s" % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
