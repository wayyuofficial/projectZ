# -*- coding: utf-8 -*-
"""목표 체류 곡선 기록이 낡았거나 곡선 밖인지 — WBS-M2 7.1.

M2 는 밸런스를 상수가 아니라 **곡선**(plans/GAMEDESIGN.md M2 절: 체류 4분 x 1.05^z, 5의 배수 구역 벽 x3)이 지킨다.
`tools/curve_check.py --out measurements/balance-M2-*.json` 이 그 곡선 대비 측정을 남기고, 이 검사는 그 기록을 본다:
  1. 기록이 게임 파일보다 새로운가 (게임을 고치고 곡선을 다시 안 쟀으면 낡은 것 — c9 와 같은 논리)
  2. 구역 10 기준 상대 도달 시각이 목표 누적의 ±20% 밖인 구역이 3개 이하인가 (M2-B1‴ 의 반증선)
  3. 벽 비·골짜기는 **정보로만** 적는다 — 지시 #65 (a): B2‴ 는 반증으로 확정하고 벽은 그대로 둔다. 잣대가 이웃 톱니에 흔들려 경고로 두면 영원히 울린다

근거: 가설(계획 M2 의 예측)이지 사례가 아니다 → 2순위. 막지 않고 경고만 한다.
곡선을 어겨서 실제로 문제가 된 사례가 1건이라도 생기면 PRIORITY 를 1로 올린다.
**판정이 아니다.** 예측의 판정은 사람이 judge_prediction.py 로 한다. 이 검사는 "지금 기록이 그 선 안에 있는가" 를 셀 뿐이다.
"""
NAME = "목표 체류 곡선 기록이 낡았거나 곡선 밖인지 (M2)"
PRIORITY = 2

import io, os, glob, json


def run(root):
    game = os.path.join(root, "game", "index.html")
    if not os.path.exists(game):
        return {"status": "skip", "detail": ["game/index.html 이 없다"]}
    recs = []
    for p in glob.glob(os.path.join(root, "measurements", "balance-M2-*.json")):
        try:
            d = json.load(io.open(p, encoding="utf-8"))
        except Exception:
            continue
        # `--no-new-weapons` 로 잰 것은 **비교용 바탕**이지 출하 곡선이 아니다.
        # 2026-09-14: 4.3 새 문구 때문에 바탕을 재다가 그게 가장 새 기록이 되어 c18 이 그걸 보고 경고했다.
        if d.get("새무기") is False:
            continue
        if isinstance(d, dict) and "도달_밖" in d and "벽" in d and d.get("벽"):
            recs.append((os.path.getmtime(p), p, d))
    if not recs:
        return {"status": "skip", "detail": ["curve_check 기록(벽 켠 것)이 없다 — python tools/curve_check.py --out measurements/balance-M2-curve-YYYY-MM-DD.json"]}
    recs.sort()
    mt, p, d = recs[-1]
    base = os.path.basename(p)
    bad = []
    if os.path.getmtime(game) > mt + 1:
        bad.append("%s 가 게임 파일보다 낡았다 — 게임을 고치고 곡선을 다시 안 쟀다" % base)
    out = d.get("도달_밖", [])
    if len(out) > 3:
        bad.append("%s: 도달 시각이 목표의 ±20%% 밖인 구역 %d개 %s (선: 3개 이하)" % (base, len(out), out))
    walls = d.get("벽비", {}) or {}
    tro = d.get("골짜기", {}) or {}
    info = "벽 비 %s · 골짜기 %s (정보 — 지시 #65 (a) 로 벽은 그대로)" % ({z: round(v, 2) for z, v in walls.items()}, tro)
    if bad:
        return {"status": "warn", "detail": bad + [info]}
    return {"status": "ok", "detail": ["%s — 도달 밖 %d개 (선 3)" % (base, len(out)), info]}
