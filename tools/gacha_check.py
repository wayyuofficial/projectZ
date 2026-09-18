# -*- coding: utf-8 -*-
"""M6 2.2/3.1 — 뽑기 확률표가 코드가 쓰는 값 그대로 도는지.

① 표 11개(0~GACHA_LV_MAX)가 각각 합 100 인가
② 단계가 오를수록 위 등급(영웅~영원) 합이 단조 증가하는가
③ 거울의 rollTierOdds(0) 을 N번 굴린 등급 분포가 TIER_ODDS[0] 과 ±1%p 안인가 (거울 = 원본과 같은 구조, c16)
④ 무기 부위 뽑기에서 해금 전 종류가 나오는가 (표본 0 이어야 한다)

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

    # 무기 풀 — 구역 1 에서는 해금 전 종류가 안 나와야 한다
    sim.G["bestZone"] = 1
    types = collections.Counter(sim.rollGear(1, "weapon", 1)["type"] for _ in range(2000))
    locked = [w["id"] for w in SP.WEAPON_TYPES if w.get("unlock", 1) > 1]
    leaked = {k: v for k, v in types.items() if k in locked}

    rec = {"측정일": datetime.date.today().isoformat(), "대상": "뽑기 확률표 — 합·단조·표본 분포·무기 풀 (M6 2.2 / 3.1)", "빌드도장": stamp,
           "도구": "tools/gacha_check.py", "표본": a.n, "시드": a.seed,
           "표_합": sums, "합_전부_100": all(abs(s - 100) < 1e-6 for s in sums),
           "위등급_합(영웅~영원)": top, "단조_증가": mono,
           "0단계_표": SP.TIER_ODDS[0], "표본_분포": dist, "차이_퍼센트포인트": diff, "±1%p_안": within,
           "무기_풀_구역1": dict(types), "해금전_종류_유출": leaked,
           "판정하지_않는다": "2.2·3.1 판정은 검증자·사람 몫."}
    print("표 합:", sums, "→", "전부 100" if rec["합_전부_100"] else "**어긋남**")
    print("위 등급 합 단조 증가:", mono, top)
    print("0단계 표본 분포:", dist, "차이:", diff, "→", "±1%p 안" if within else "**밖**")
    print("구역 1 무기 풀:", dict(types), "해금 전 유출:", leaked or "0")
    if a.out:
        io.open(os.path.join(ROOT, a.out), "w", encoding="utf-8").write(json.dumps(rec, ensure_ascii=False, indent=2))
        print("기록:", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
