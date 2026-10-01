# -*- coding: utf-8 -*-
"""M6 2.2/3.1 — 뽑기 확률표가 코드가 쓰는 값 그대로 도는지.

① 표 11개(0~GACHA_LV_MAX)가 각각 합 100 인가
② 단계가 오를수록 위 등급(영웅~영원) 합이 단조 증가하는가
③ 거울의 rollTierOdds(0) 을 N번 굴린 등급 분포가 TIER_ODDS[0] 과 ±1%p 안인가 (거울 = 원본과 같은 구조, c16)
④ (M10 — 무기 해금 구역이 없어져 '해금 전 유출' 은 은퇴) **뽑기에서 영원이 나오는가** — 입수 레벨 0~최대 전부, 표본 0 이어야 한다(지시 #155: 영원은 융합으로만)

판정하지 않는다 — 숫자를 기록에 남기고, WBS 2.2·3.1 의 판정은 검증자·사람이 한다.
"""
import sys, os, io, json, argparse, hashlib, datetime, collections
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import tools.sim_port as SP


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    stamp = hashlib.sha256(io.open(os.path.join(ROOT, "game", "index.html"), "rb").read()).hexdigest()[:16]

    sums = [round(sum(r), 6) for r in SP.TIER_ODDS]
    top = [round(sum(r[4:]), 3) for r in SP.TIER_ODDS]          # 영웅·전설·초월·영원
    mono = all(top[i + 1] >= top[i] for i in range(len(top) - 1))

    sim = SP.Sim(seed=a.seed) if hasattr(SP, "Sim") else None
    if sim is None:
        cls = next(getattr(SP, n) for n in dir(SP) if isinstance(getattr(SP, n), type) and hasattr(getattr(SP, n), "rollTierOdds"))
        sim = cls(seed=a.seed)
    cnt = collections.Counter(sim.rollTierOdds(0) for _ in range(a.n))
    dist = [round(100.0 * cnt.get(i + 1, 0) / a.n, 2) for i in range(len(SP.TIER_ODDS[0]))]
    diff = [round(d - e, 2) for d, e in zip(dist, SP.TIER_ODDS[0])]
    within = all(abs(x) <= 1.0 for x in diff)

    # M10 — 영원(마지막 등급)은 뽑기로 안 나온다. 입수 레벨마다 gachaRoll 을 굴린다(부위 무작위 — 무기 종류는 무기 칸만 센다).
    eternal = {}
    types = collections.Counter()
    for lv in range(len(SP.TIER_ODDS)):
        sim.curGachaLv = (lambda lv=lv: lv)
        gs = [sim.gachaRoll() for _ in range(max(1, a.n // len(SP.TIER_ODDS)))]   # 게임 뽑기와 같은 길(입수 레벨 확률표)
        eternal[lv] = sum(1 for g in gs if g["tier"] >= len(SP.TIER_ODDS[0]))
        if lv == 0:
            types.update(g["type"] for g in gs if g["slot"] == "weapon")

    rec = {"측정일": datetime.date.today().isoformat(), "대상": "뽑기 확률표 — 합·단조·표본 분포·영원 0 (M6 2.2 / 3.1 · M10)", "빌드도장": stamp,
           "도구": "tools/gacha_check.py", "표본": a.n, "시드": a.seed,
           "표_합": sums, "합_전부_100": all(abs(s - 100) < 1e-6 for s in sums),
           "위등급_합(영웅~영원)": top, "단조_증가": mono,
           "0단계_표": SP.TIER_ODDS[0], "표본_분포": dist, "차이_퍼센트포인트": diff, "±1%p_안": within,
           "무기_종류_0단계": dict(types), "영원_표본_입수레벨별": eternal, "영원_0": not any(eternal.values()),
           "판정하지_않는다": "2.2·3.1 판정은 검증자·사람 몫."}
    print("표 합:", sums, "→", "전부 100" if rec["합_전부_100"] else "**어긋남**")
    print("위 등급 합 단조 증가:", mono, top)
    print("0단계 표본 분포:", dist, "차이:", diff, "→", "±1%p 안" if within else "**밖**")
    print("0단계 무기 종류:", dict(types))
    print("뽑기 영원(입수 레벨별):", eternal, "→", "0 (융합으로만)" if not any(eternal.values()) else "**나왔다**")
    if a.out:
        io.open(os.path.join(ROOT, a.out), "w", encoding="utf-8").write(json.dumps(rec, ensure_ascii=False, indent=2))
        print("기록:", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
