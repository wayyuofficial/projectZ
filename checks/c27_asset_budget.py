# -*- coding: utf-8 -*-
"""게임 파일 크기 예산 — 그림을 data URI 로 넣는 만큼 game/index.html 이 커진다 (M9 5.1, 예측 M9-P1).

근거: M8·M9 에서 배경 30장·주인공·무기·효과·좀비·보스·장비·UI 그림을 전부 data URI 로 넣었다(파일 하나 규칙 c6).
폰 WebView 는 이 파일 하나를 통째로 읽고 파싱한다 — 커질수록 첫 화면이 늦다. 상한을 숫자로 두고 넘으면 막는다.
상한 5MB(5,000,000 바이트) — 지시 #157(M11, 구역 31~60 그림). 이력: 3.2MB 는 plans/plan-M9.md 의 M9-P1. 바꾸려면 계획서와 함께 사람이 바꾼다.

## 무엇을 보는가
- game/*.html 각각의 바이트 수 ≤ 상한 → ok, 넘으면 fail
- 참고로 그림 블록(const XXX_ART / BG_IMG_SRC / HERO_ANIM)별 data URI 문자 수를 적는다 — 어디가 큰지 보이게

## 이 검사가 못 보는 것 (숨기지 않는다)
실제 로딩 시간·메모리(디코드한 그림 크기)는 못 잰다 — 폰·에뮬레이터가 잰다. 파일 크기는 대리 지표다.
"""
NAME = "게임 파일 크기 예산(그림 data URI)"
PRIORITY = 2

import io, os, re, glob

LIMIT = 5000000   # M11 (지시 #157): 사람 "상한 5MB로" — 구역 31~60 그림. 이력: 3.2MB(M9-P1)


def run(root):
    limit = int(os.environ.get("C27_LIMIT", LIMIT))   # 자기시험(tools/selftest_checks.py)이 낮춰서 fail 을 본다
    games = sorted(glob.glob(os.path.join(root, "game", "*.html")))
    if not games:
        return {"status": "skip", "detail": ["game/*.html 이 아직 없다"]}
    bad, info = [], []
    for p in games:
        base = os.path.basename(p); size = os.path.getsize(p)
        txt = io.open(p, encoding="utf-8-sig", errors="replace").read()
        parts = []
        for m in re.finditer(r"const (\w+) = \{", txt):
            name = m.group(1)
            if not (name.endswith("_ART") or name in ("BG_IMG_SRC", "HERO_ANIM")): continue
            j = txt.find("};", m.start()); j = len(txt) if j < 0 else j   # 블록 끝(HERO_ANIM 은 같은 줄에서 닫힌다)
            n = sum(len(u) for u in re.findall(r"data:image/[a-z]+;base64,[A-Za-z0-9+/=]+", txt[m.start():j]))
            if n: parts.append("%s %.0fK" % (name, n / 1000))
        idir = os.path.join(os.path.dirname(p), "img")   # M25 (지시 #190) — 그림을 뺀 뒤엔 img 폴더 합계를 같이 적는다(상한은 게임 파일에만)
        if os.path.isdir(idir):
            fs = os.listdir(idir); parts.append("img/ %d개 %.2fMB" % (len(fs), sum(os.path.getsize(os.path.join(idir, f)) for f in fs) / 1e6))
        line = "%s : %.2fMB / 상한 %.2fMB — %s" % (base, size / 1e6, limit / 1e6, " · ".join(parts) or "그림 블록 없음")
        (bad if size > limit else info).append(line)
    if bad:
        return {"status": "fail", "detail": bad + ["상한을 넘었다 — WebP 품질·프레임 수·배율을 낮춘다(M9-P1 반증 조건)"]}
    return {"status": "ok", "detail": info}
