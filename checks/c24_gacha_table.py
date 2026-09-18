# -*- coding: utf-8 -*-
"""뽑기 확률표가 **코드가 쓰는 값 하나**인지 — 표가 성한지, 팝업이 그 표를 읽는지.

근거: canon/10-scope.md '장비 뽑기' 행 — "확률표는 게임 안 팝업에 **코드가 쓰는 값 그대로** 표시한다" (지시 #120·#121, 정본 승인 2026-09-18).
확률 표시는 법(확률형 아이템 표시 의무)에도 걸리는 것이라, 표와 팝업이 둘로 갈라지면 게임이 거짓말을 한다.

## 무엇을 보는가
1. `TIER_ODDS` 행 수 = `GACHA_LV_MAX` + 1, 각 행 8칸(등급 수), **합 100** (±1e-6)
2. 단계가 오를수록 위 등급(영웅~영원 = 5~8번째 칸) 합이 **줄지 않는다** (정본 '뽑기 강화' 행: "단계가 오르면 높은 등급 확률이 오른다")
3. `drawOdds` 본문이 `TIER_ODDS` 를 읽고, 안에 **퍼센트 리터럴**(`12.3%` · `'40%'`)이 없다 — 따로 적은 숫자가 있으면 표와 갈라질 수 있다

## 이 검사가 못 보는 것 (숨기지 않는다)
`rollTierOdds` 가 그 표대로 굴리는지는 여기서 안 본다 — `tools/gacha_check.py` 가 표본으로 재고 기록에 남긴다.
"""
NAME = "뽑기 확률표가 코드가 쓰는 값 하나인지 (표 합·단조·팝업이 표를 읽음)"
PRIORITY = 1

import io, os, re, glob


def _matrix(txt, name):
    m = re.search(r"const\s+" + name + r"\s*=\s*\[(.*?)\n\];", txt, re.S)
    if not m:
        return None
    body = re.sub(r"//[^\n]*", "", m.group(1))
    return [[float(v) for v in re.findall(r"-?[\d.]+", row)] for row in re.findall(r"\[([^\[\]]*)\]", body)]


def run(root):
    games = sorted(glob.glob(os.path.join(root, "game", "*.html")))
    if not games:
        return {"status": "skip", "detail": ["game/*.html 이 없다"]}
    bad, okd = [], []
    for g in games:
        base = os.path.relpath(g, root)
        txt = io.open(g, encoding="utf-8-sig").read()
        if "TIER_ODDS" not in txt:
            continue                                   # 뽑기가 없는 게임(옛 본보기)은 대상이 아니다
        odds = _matrix(txt, "TIER_ODDS")
        mm = re.search(r"const\s+GACHA_LV_MAX\s*=\s*(\d+)", txt)
        names = re.search(r"const\s+TIER_NAMES\s*=\s*\[(.*?)\]", txt)
        n_tier = len(re.findall(r"'[^']*'", names.group(1))) if names else 8
        if odds is None or not mm:
            bad.append("%s : TIER_ODDS 또는 GACHA_LV_MAX 를 못 읽었다" % base); continue
        lv_max = int(mm.group(1))
        if len(odds) != lv_max + 1:
            bad.append("%s : TIER_ODDS 행 %d개 ≠ GACHA_LV_MAX+1 = %d" % (base, len(odds), lv_max + 1))
        for i, row in enumerate(odds):
            if len(row) != n_tier:
                bad.append("%s : TIER_ODDS[%d] 칸 %d개 ≠ 등급 %d" % (base, i, len(row), n_tier))
            if abs(sum(row) - 100) > 1e-6:
                bad.append("%s : TIER_ODDS[%d] 합 %.3f ≠ 100" % (base, i, sum(row)))
        tops = [sum(r[4:]) for r in odds if len(r) >= 8]
        for i in range(1, len(tops)):
            if tops[i] + 1e-9 < tops[i - 1]:
                bad.append("%s : 위 등급 합이 Lv%d(%.1f) → Lv%d(%.1f) 로 준다 — 정본 '단계가 오르면 높은 등급 확률이 오른다'" % (base, i - 1, tops[i - 1], i, tops[i]))
                break
        dm = re.search(r"function drawOdds\(\)\s*\{(.*?)\n\}\n", txt, re.S)
        if not dm:
            bad.append("%s : drawOdds 가 없다 — 확률 팝업은 정본 항목이다" % base)
        else:
            body = dm.group(1)
            if "TIER_ODDS" not in body:
                bad.append("%s : drawOdds 가 TIER_ODDS 를 안 읽는다 — 표가 둘이 된다" % base)
            lits = re.findall(r"\b\d+(?:\.\d+)?%|'\d+(?:\.\d+)?%'", body)
            if lits:
                bad.append("%s : drawOdds 안에 퍼센트 리터럴 %s — 표를 읽어 그려야 한다" % (base, lits[:3]))
        if not [b for b in bad if b.startswith(base)]:
            okd.append("%s (Lv 0~%d, 등급 %d, 팝업이 표를 읽음)" % (base, lv_max, n_tier))
    if bad:
        return {"status": "fail", "detail": bad}
    if not okd:
        return {"status": "skip", "detail": ["TIER_ODDS 가 있는 게임이 없다"]}
    return {"status": "ok", "detail": okd}
