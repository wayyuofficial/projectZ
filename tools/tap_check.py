# -*- coding: utf-8 -*-
"""탭 대상이 최소 크기를 지키는지 — 판정 7.1.

기기 폭·높이를 훑으며 **모든 탭**의 버튼 자리를 만들고, 가장 작은 탭 대상을 CSS px 로 잰다.
선은 게임의 `MIN_TAP_CSS` 다 (숫자를 여기 적지 않는다 — c2 가 18차·M2 에서 두 번 낡은 그 실수다).

**무엇을 재는가 — 이 지표는 두 번 고쳤다.** (2026-09-15, tap-m4-1 기록)

1. 처음엔 기하학적 최소를 쟀다 → 0.61 px. 그건 **스크롤로 잘린 줄**이고 `hitButton` 이 이미 건너뛴다.
2. 가드를 적용해 재니 29.04 px. 그런데 가드가 29 에서 자르므로 **그 지표로는 배치를 못 잰다** —
   무엇을 하든 항상 29 근처가 나오는 **항등식**이 된다 (12차 감사의 그 구멍).
3. 그래서 **잘리지 않는 고정 버튼만** 잰다. 배치가 바뀌는 대상이 그것이다.

쓰는 법:
    python tools/tap_check.py --out measurements/tap-YYYY-MM-DD.json
"""
import io, os, sys, json, argparse, hashlib, datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # cp949 콘솔에서 '—' 로 죽어 기록을 못 남겼다 (30차 감사)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim_port as S

TABS = ("stat", "weapon", "gear", "daily")   # 지시 #151: "daily" 는 이제 탭이 아니라 미션 팝업 상태


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", type=int, default=4, help="뷰포트 훑는 간격 px")
    ap.add_argument("--out")
    a = ap.parse_args(argv[1:])

    s = S.Sim(seed=1)
    s.G["hp"] = s.maxHP()
    # 가방을 채워 목록이 가장 길 때를 본다 (M4 3.4 와 같은 조건)
    for i in range(8):
        s.G["bag"].append(s.rollGear(3))

    best = None
    n = 0
    for vw in range(280, 501, a.step):
        for vh in range(560, 1001, a.step):
            fit = S.fit_game(vw, vh)
            css_per = fit["scale"]              # 논리 1px 당 CSS px
            for tab in TABS:
                s.tab = "stat" if tab == "daily" else tab
                s.dailyPopup = (tab == "daily")
                for b in s.buildButtons():
                    if b.get("clip"):
                        continue               # 잘릴 수 있는 줄은 안 잰다 (위 3번)
                    n += 1
                    w, h = b["w"] * css_per, b["h"] * css_per
                    small = min(w, h)
                    if best is None or small < best[0]:
                        best = (small, dict(뷰포트=[vw, vh], 탭=tab, 대상=b["kind"],
                                            폭=round(w, 2), 높이=round(h, 2)))

    line = S.MIN_TAP_CSS
    ok = best[0] >= line
    print("고정 버튼 표본 %d개" % n)
    print("가장 작은 탭 대상: %.2f CSS px  (선 %.0f)" % (best[0], line))
    print("  자리: %s" % json.dumps(best[1], ensure_ascii=False))
    print("결과: %s" % ("통과" if ok else "**미달**"))

    if a.out:
        stamp = hashlib.sha256(io.open(S.GAME, "rb").read()).hexdigest()[:16]
        rec = {"측정일": datetime.date.today().isoformat(),
               "대상": "탭 %d개 배치가 7.1(탭 대상 >= MIN_TAP_CSS)을 지키는지" % len(TABS),
               "빌드도장": stamp, "도구": "tools/tap_check.py",
               "방법": "sim_port 의 fit_game·buildButtons 로 280~500 x 560~1000 을 %dpx 씩 훑고 탭 %d개를 전부 본다. 가방에 장비 8개를 넣고 잰다. **잘리지 않는 고정 버튼만** 잰다(잘린 줄은 hitButton 이 건너뛴다)." % (a.step, len(TABS)),
               "표본": n, "최소_CSS_px": round(best[0], 2), "가장_작은_자리": best[1],
               "선": line, "결과": "통과" if ok else "미달",
               "판정하지_않는다": "판정은 검증자·사람 몫이다. 여기는 만든 쪽의 측정이다."}
        io.open(a.out, "w", encoding="utf-8").write(json.dumps(rec, ensure_ascii=False, indent=2))
        print("기록: %s" % a.out)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
