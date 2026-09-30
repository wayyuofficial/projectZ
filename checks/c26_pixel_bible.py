# -*- coding: utf-8 -*-
"""도트 자산이 아트 바이블을 지키는지 — 램프 밖 색 0 · 격자 규격 · 아웃라인 순검정 아님.

근거: plans/plan-M7.md (지시 #132, 2026-09-30) — "이미지가 따로 논다" 의 원인은 색이 아니라 화풍 혼재다.
한 격자·한 램프·한 아웃라인 규칙을 코드가 지키게 한다. 눈으로 보는 것(한 세트로 보이나)은 폰이 한다.

## 무엇을 보는가
`const SPRITES = { ... };` 안에서
  1. 범례(legend) 값이 전부 `R.<계열>[n]`(= PALETTE.ramp) 참조인가 — hex·rgb 리터럴 0
  2. 프레임의 모든 줄 길이가 같고, (폭, 높이) 가 `PX_GRIDS` 안인가
  3. 범례 키 'O'(아웃라인)가 있으면 램프 4단(index 3)을 가리키는가 — 순검정 금지는 램프 값이 담보한다(#000 없음)
그리고 `PALETTE.ramp` 의 28색에 `#000000`·`#000` 이 없는가.

## 이 검사가 못 보는 것 (숨기지 않는다)
광원 방향·SD 비율·실루엣 가독성은 코드로 못 본다 — 스크린샷과 폰이 본다.
"""
NAME = "도트 자산이 아트 바이블(램프·격자·아웃라인)을 지키는지"
PRIORITY = 2

import io, os, re, glob


def run(root):
    games = sorted(glob.glob(os.path.join(root, "game", "*.html")))
    bad, okd = [], []
    for g in games:
        base = os.path.relpath(g, root)
        txt = io.open(g, encoding="utf-8-sig").read()
        if "const SPRITES = {" not in txt:
            continue
        # 램프
        rm = re.search(r"ramp:\s*\{(.*?)\n\s*\},", txt, re.S)
        if not rm:
            bad.append("%s : PALETTE.ramp 를 못 찾았다" % base); continue
        cols = re.findall(r"#[0-9A-Fa-f]{6}|#[0-9A-Fa-f]{3}\b", rm.group(1))
        if any(c.lower() in ("#000000", "#000") for c in cols):
            bad.append("%s : 램프에 순검정이 있다 — 아웃라인은 올리브·녹이 섞인 어두운 색이어야 한다" % base)
        # 격자 규격
        gm = re.search(r"const PX_GRIDS\s*=\s*\[(.*?)\];", txt)
        grids = set(tuple(int(v) for v in re.findall(r"\d+", pair)) for pair in re.findall(r"\[(\d+,\s*\d+)\]", gm.group(1))) if gm else set()
        # SPRITES 블록
        i = txt.index("const SPRITES = {"); j = txt.index("\n};", i)
        block = txt[i:j]
        lits = re.findall(r"#[0-9A-Fa-f]{6}\b|#[0-9A-Fa-f]{3}\b|rgba?\(", block)
        if lits:
            bad.append("%s : SPRITES 범례에 직접 색 %d개 %s — R.<계열>[n] 만" % (base, len(lits), lits[:3]))
        for lm in re.finditer(r"legend:\s*\{([^}]*)\}", block):
            vals = re.findall(r"\b[A-Za-z]\s*:\s*([^,}]+)", lm.group(1))
            for v in vals:
                v = v.strip()
                if not re.match(r"^R\.\w+\[[0-3]\]$", v):
                    bad.append("%s : 범례 값 '%s' 가 R.<계열>[0~3] 이 아니다" % (base, v)); break
        for fm in re.finditer(r"(\w+):\s*\[\s*((?:'[^']*',?\s*)+)\]", block):
            rows = re.findall(r"'([^']*)'", fm.group(2))
            if len(rows) < 4:
                continue                      # 범례 등 짧은 배열은 프레임이 아니다
            w = len(rows[0]); h = len(rows)
            if any(len(r) != w for r in rows):
                bad.append("%s : 프레임 '%s' 줄 길이가 다르다" % (base, fm.group(1)))
            elif grids and (w, h) not in grids:
                bad.append("%s : 프레임 '%s' 격자 %dx%d 가 PX_GRIDS %s 밖" % (base, fm.group(1), w, h, sorted(grids)))
        if not [b for b in bad if b.startswith(base)]:
            okd.append("%s (램프 %d색, 격자 %s)" % (base, len(cols), sorted(grids)))
    if bad:
        return {"status": "fail", "detail": bad}
    if not okd:
        return {"status": "skip", "detail": ["SPRITES 가 있는 게임이 없다 (M7 전)"]}
    return {"status": "ok", "detail": okd}
