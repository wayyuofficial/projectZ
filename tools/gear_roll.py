# -*- coding: utf-8 -*-
"""장비 생성기 분포 — M4 3.3.

`rollGear(z)` 를 구역마다 여러 번 불러 **부위가 고르게 나오는지 · 옵션 줄이 상한을 안 넘는지 ·
등급 중심이 구역과 함께 오르는지**를 센다.

상한(부위 4 · 모양 3 · 옵션 2줄)은 정본이 정하고 `c2` 가 막는다. 여기서는 **분포**를 본다 —
상한 안이어도 한 부위만 쏟아지면 "다음 장비가 뭘까" 가 성립하지 않는다.

**이 파일이 있는 이유**: 2026-09-15 측정은 브라우저에서 일회용으로 돌렸다. 그러면 빌드가
바뀔 때마다(R005) 다시 재기가 비싸서 값을 손으로 옮기게 된다 — 사례 17 이 그것이다.
`rollGear` 는 `sim_port` 가 거울로 들고 있고 `c16` 이 어긋나면 막으므로 여기서 그냥 부르면 된다.

**난수는 게임과 같지 않다** (sim_port 머리말 3). 그래서 시드 하나의 값을 게임의 값이라고
말하지 않는다 — 여기서 보는 것은 **분포**다.

쓰는 법:
    python tools/gear_roll.py --n 10000 --out measurements/gear-roll-YYYY-MM-DD.json
"""
import io, os, sys, json, argparse, hashlib, datetime, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim_port as S

SLOT_LINE = 10.0        # 부위 편차 선 (±%)
ZONES = (1, 15, 30)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10000)
    ap.add_argument("--out")
    a = ap.parse_args(argv[1:])

    s = S.Sim(seed=1)
    tier_dist, slots, lines = {}, collections.Counter(), collections.Counter()
    for z in ZONES:
        c = collections.Counter()
        for _ in range(a.n):
            g = s.rollGear(z)
            c[g["tier"]] += 1
            if z == ZONES[1]:                 # 부위·옵션은 한 구역에서만 센다 (표본을 섞지 않는다)
                slots[g["slot"]] += 1
                lines[len(g.get("affixes") or [])] += 1
        tier_dist["구역 %d" % z] = dict(sorted(c.items()))

    armor = {k: v for k, v in slots.items() if k != "weapon"}
    design = float(a.n) / max(1, len(armor))
    dev = max(abs(v - design) / design * 100.0 for v in armor.values()) if armor else 0.0
    over = sum(v for k, v in lines.items() if k > S.GEAR_AFFIXES)

    print("표본 %d개 x 구역 %s" % (a.n, list(ZONES)))
    for z, d in tier_dist.items():
        print("  %s 등급: %s" % (z, d))
    print("부위 분포(구역 %d): %s · 설계값 %.0f · 최대 편차 %.1f%% (선 ±%.0f%%)"
          % (ZONES[1], dict(armor), design, dev, SLOT_LINE))
    print("옵션 줄 수: %s · 상한 %d줄 초과 %d개" % (dict(sorted(lines.items())), S.GEAR_AFFIXES, over))
    ok = dev <= SLOT_LINE and over == 0
    print("결과: %s" % ("통과" if ok else "**미달**"))

    if a.out:
        stamp = hashlib.sha256(io.open(S.GAME, "rb").read()).hexdigest()[:16]
        rec = {"측정일": datetime.date.today().isoformat(),
               "대상": "장비 생성기 분포 — M4 3.3", "빌드도장": stamp,
               "도구": "tools/gear_roll.py",
               "방법": "sim_port 가 거울로 든 rollGear(z) 를 구역 %s 마다 %d회 부른다. 부위·옵션은 구역 %d 표본만 센다." % (list(ZONES), a.n, ZONES[1]),
               "표본": a.n, "등급_분포": tier_dist,
               "부위_분포": dict(armor), "부위_설계값": design,
               "부위_최대_편차_퍼센트": round(dev, 1),
               "옵션_줄수": {str(k) + "줄": v for k, v in sorted(lines.items())},
               "옵션_상한_초과": over, "선": {"부위_편차_퍼센트": SLOT_LINE, "옵션_줄": S.GEAR_AFFIXES},
               "결과": "통과" if ok else "미달",
               "난수_주의": "포트의 난수는 게임의 Math.random() 과 같지 않다. 시드 하나의 값이 아니라 분포로만 말한다.",
               "판정하지_않는다": "M4 판정은 검증자·사람 몫이다."}
        io.open(a.out, "w", encoding="utf-8").write(json.dumps(rec, ensure_ascii=False, indent=2))
        print("기록: %s" % a.out)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
