# -*- coding: utf-8 -*-
"""업그레이드 간격이 정본의 상한을 넘는지 — WBS-M3 2.1.

사람이 실기에서 말한 것: *"초반 30구역 업그레이드가 너무 오래 걸린다."* (2026-09-11)
목표 **체류** 곡선은 그 느낌을 못 잰다 — 체류가 짧아도 그 안에서 아무것도 안 올라가면 느리다.
그래서 정본이 **업그레이드 간격 상한**을 따로 들고 있다 (`canon/10-scope.md`: `SCOPE_UPGRADE_GAP_MAX_SEC`).

**숫자를 이 파일에 적지 않는다.** 정본에서 읽는다 — c2 의 교훈("숫자를 여기 적지 않는다. 18차·M2 에서 두 번 낡았다").

## 무엇을 보는가
`tools/upgrade_cadence.py --out measurements/upgrade-cadence-*.json` 이 남긴 **가장 새 기록**에 대해:
  1. 기록이 게임 파일보다 새로운가 (게임을 고치고 다시 안 쟀으면 낡은 것)
  2. 어느 구역이든 **중앙 간격**이 정본 상한을 넘는가

## 이 검사가 못 보는 것 (숨기지 않는다)
- **중앙값만 본다.** 한 시드에서 길게 비는 구간은 중앙에 묻힌다.
- 매수 정책은 `auto_run` 의 "가장 싼 것부터" 다. 사람은 그렇게 안 살 수 있다 — 사람의 간격은 이보다 길 수 있다.
- **판정이 아니다.** `M3-B2` 의 판정은 사람이 `judge_prediction.py` 로 한다. 이 검사는 선 안인지 셀 뿐이다.
"""
NAME = "업그레이드 간격이 정본 상한을 넘는지 (M3)"
PRIORITY = 2

import io, os, re, glob, json


def _limit(root):
    txt = io.open(os.path.join(root, "canon", "10-scope.md"), encoding="utf-8").read()
    m = re.search(r"^\s*SCOPE_UPGRADE_GAP_MAX_SEC\s*=\s*([0-9.]+)\s*$", txt, re.M)
    return float(m.group(1)) if m else None


def run(root):
    game = os.path.join(root, "game", "index.html")
    if not os.path.exists(game):
        return {"status": "skip", "detail": ["game/index.html 이 없다"]}
    lim = _limit(root)
    if lim is None:
        return {"status": "error", "detail": ["canon/10-scope.md 에 SCOPE_UPGRADE_GAP_MAX_SEC 가 없다"]}

    recs = []
    for p in glob.glob(os.path.join(root, "measurements", "upgrade-cadence-*.json")):
        try:
            d = json.load(io.open(p, encoding="utf-8"))
        except Exception:
            continue
        if isinstance(d, dict) and d.get("구역별"):
            recs.append((os.path.getmtime(p), p, d))
    if not recs:
        return {"status": "skip",
                "detail": ["업그레이드 간격 기록이 없다 — python tools/upgrade_cadence.py --out measurements/upgrade-cadence-YYYY-MM-DD.json"]}
    recs.sort()
    mt, p, d = recs[-1]
    base = os.path.basename(p)

    bad = []
    if os.path.getmtime(game) > mt + 1:
        bad.append("%s 가 게임 파일보다 낡았다 — 게임을 고치고 간격을 다시 안 쟀다" % base)
    over = [(r["구역"], r["간격_초_중앙"]) for r in d["구역별"]
            if r.get("간격_초_중앙") is not None and r["간격_초_중앙"] > lim]
    if over:
        bad.append("%s: 중앙 간격이 상한 %.0f초를 넘는 구역 %d개 — %s (정본 SCOPE_UPGRADE_GAP_MAX_SEC)"
                   % (base, lim, len(over), ["%d:%.0f초" % (z, g) for z, g in over[:8]]))
    thin = d.get("매수_3회_미만_구역") or []
    if thin:
        bad.append("%s: 업그레이드가 3회 미만인 구역 %s — 올릴 게 없는 구역이다" % (base, thin))

    gaps = [r["간격_초_중앙"] for r in d["구역별"] if r.get("간격_초_중앙") is not None]
    info = "구역 %d개 · 간격 중앙 %.0f~%.0f초 (상한 %.0f)" % (len(gaps), min(gaps), max(gaps), lim) if gaps else "-"
    if bad:
        return {"status": "warn", "detail": bad + [info]}
    return {"status": "ok", "detail": ["%s — 상한 %.0f초 안" % (base, lim), info]}
