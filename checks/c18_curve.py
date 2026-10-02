# -*- coding: utf-8 -*-
"""목표 체류 곡선 기록이 낡았거나 곡선 밖인지 — WBS-M3 1.2.

밸런스는 상수가 아니라 **곡선**이 지킨다. 곡선은 정본이 정하고(`canon/10-scope.md`: 체류 0.6분 x 1.12^(z-1), 구역 1~30, 벽 x2),
`tools/curve_check.py --out measurements/balance-M3-*.json` 이 그 곡선 대비 측정을 남긴다. 이 검사는 그 기록을 본다:
  1. 기록이 게임 파일보다 새로운가 (게임을 고치고 곡선을 다시 안 쟀으면 낡은 것 — c9 와 같은 논리)
  2. **체류**가 목표의 ±20% 밖인 구역이 4개 미만인가 (M3-B1 의 반증선)
  3. 도달 시각·벽 비·골짜기는 **정보로만** 적는다 — M3 의 판정선은 체류다. 벽은 지시 #65 (a) 로 그대로 둔다

**가장 새 기록 하나만 본다.** 목표 공식이 바뀌면 옛 기록은 다른 선으로 잰 것이라 섞으면 거짓이다 —
그래서 이름이 아니라 **시각**으로 고른다. 이름에 마일스톤을 박으면 다음 마일스톤 기록을 놓친다(2026-09-15 M4 에서 겪었다).

M15 (지시 #164) — **판정선은 정본이 고른다.** `canon/10-scope.md` 기계값에 `SCOPE_ARRIVE_TOL` 이 있으면
**누적 도달 시각**이 목표 누적의 ±그 값 밖인 구역이 4개 미만인가를 본다(구역별 체류는 정보로 내린다).
구역별 체류 ±20% 는 벽·골짜기(한 구역이 길면 다음이 짧다)를 그대로 세어 42/59 구역이 늘 밖이었다 — **늘 켜진 경고는 아무도 안 본다**(분석 C5).
정본에 그 값이 없으면 예전 선(체류)을 쓴다 — 정본이 승인되기 전에는 이 검사의 선이 바뀌지 않는다.

근거: 가설(계획 M2 의 예측)이지 사례가 아니다 → 2순위. 막지 않고 경고만 한다.
곡선을 어겨서 실제로 문제가 된 사례가 1건이라도 생기면 PRIORITY 를 1로 올린다.
**판정이 아니다.** 예측의 판정은 사람이 judge_prediction.py 로 한다. 이 검사는 "지금 기록이 그 선 안에 있는가" 를 셀 뿐이다.
"""
NAME = "목표 체류 곡선 기록이 낡았거나 곡선 밖인지 (선은 정본이 정한다)"
PRIORITY = 2

import io, os, re, glob, json


def _arrive_tol(root):
    """정본 기계값 SCOPE_ARRIVE_TOL (없으면 None — 예전 선)."""
    try:
        txt = io.open(os.path.join(root, "canon", "10-scope.md"), encoding="utf-8").read()
    except Exception:
        return None
    m = re.search(r"^\s*SCOPE_ARRIVE_TOL\s*=\s*([0-9.]+)\s*$", txt, re.M)
    return float(m.group(1)) if m else None


def run(root):
    game = os.path.join(root, "game", "index.html")
    if not os.path.exists(game):
        return {"status": "skip", "detail": ["game/index.html 이 없다"]}
    recs = []
    # M4 3 부터 기록 이름이 balance-M4-* 다. **마일스톤 이름을 검사에 박지 않는다** —
    # M3 에서 balance-M2-* 만 보게 했다가 M4 기록을 놓쳤다(2026-09-15).
    for p in glob.glob(os.path.join(root, "measurements", "balance-M[0-9]*-*.json")):
        try:
            d = json.load(io.open(p, encoding="utf-8"))
        except Exception:
            continue
        # `--no-new-weapons` 로 잰 것은 **비교용 바탕**이지 출하 곡선이 아니다.
        # 2026-09-14: 4.3 새 문구 때문에 바탕을 재다가 그게 가장 새 기록이 되어 c18 이 그걸 보고 경고했다.
        if d.get("새무기") is False:
            continue
        if isinstance(d, dict) and "곡선밖" in d and "벽" in d and d.get("벽"):
            recs.append((os.path.getmtime(p), p, d))
    if not recs:
        return {"status": "skip", "detail": ["curve_check 기록(벽 켠 것)이 없다 — python tools/curve_check.py --out measurements/balance-M4-curve-YYYY-MM-DD.json"]}
    recs.sort()
    mt, p, d = recs[-1]
    base = os.path.basename(p)
    bad = []
    if os.path.getmtime(game) > mt + 1:
        bad.append("%s 가 게임 파일보다 낡았다 — 게임을 고치고 곡선을 다시 안 쟀다" % base)
    walls = d.get("벽비", {}) or {}
    tro = d.get("골짜기", {}) or {}
    tol = _arrive_tol(root)
    if tol is not None:   # M15 — 정본이 고른 선: 누적 도달 시각
        ratio = d.get("도달비", {}) or {}
        out = sorted(int(z) for z, r in ratio.items() if abs(r - 1) > tol + 1e-9) if ratio else d.get("도달_밖", [])
        if len(out) >= 4:
            bad.append("%s: 누적 도달 시각이 목표의 ±%d%% 밖인 구역 %d개 %s (선: 4개 미만 — 정본 SCOPE_ARRIVE_TOL)" % (base, round(tol * 100), len(out), out))
        info = "체류 밖 %d개 · 벽 비 %s · 골짜기 %s (전부 정보 — 판정선은 누적 도달 시각이다)" % (
            len(d.get("곡선밖", [])), {z: round(v, 2) for z, v in walls.items()}, tro)
        if bad:
            return {"status": "warn", "detail": bad + [info]}
        return {"status": "ok", "detail": ["%s — 도달 밖 %d개 %s (선 4 미만, ±%d%%)" % (base, len(out), out, round(tol * 100)), info]}
    out = d.get("곡선밖", [])
    if len(out) >= 4:
        bad.append("%s: 체류가 목표의 ±20%% 밖인 구역 %d개 %s (선: 4개 미만 — M3-B1)" % (base, len(out), out))
    info = "도달 밖 %s · 벽 비 %s · 골짜기 %s (전부 정보 — 판정선은 체류다)" % (
        d.get("도달_밖", []), {z: round(v, 2) for z, v in walls.items()}, tro)
    if bad:
        return {"status": "warn", "detail": bad + [info]}
    return {"status": "ok", "detail": ["%s — 체류 밖 %d개 (선 4 미만)" % (base, len(out)), info]}
