# -*- coding: utf-8 -*-
"""게임 HTML에 문자 인코딩과 뷰포트 선언이 있는지.

근거: cases/2026-09-08-08-실기에서만.md (실기 LG V30에서 한글 깨짐)

**1회 관측인데 왜 바로 검사로 내렸는가**
승격 조건 2회는 "판단이 갈리는 패턴"에 대한 것이다. 이건 판단이 아니다 —
선언이 없으면 기기에 따라 **반드시** 깨진다. 결정적이고 셀 수 있으므로 1순위로 둔다.
(C7 도 같은 이유로 1회 관측에서 1순위로 내렸다.)
"""
NAME = "게임 HTML에 charset·뷰포트 선언이 있는지"
PRIORITY = 1

import io, os, re, glob

CHARSET = re.compile(r'<meta[^>]+charset\s*=\s*["\']?\s*utf-8', re.I)
VIEWPORT = re.compile(r'<meta[^>]+name\s*=\s*["\']?viewport', re.I)
VP_COVER = re.compile(r'viewport-fit\s*=\s*cover', re.I)
VP_WIDTH = re.compile(r'width\s*=\s*device-width', re.I)
HEAD_BYTES = 1024   # 브라우저는 앞부분만 훑어 인코딩을 정한다


def run(root):
    games = sorted(glob.glob(os.path.join(root, "game", "*.html")))
    if not games:
        return {"status": "skip", "detail": ["game/*.html 이 없다"]}

    bad = []
    for p in games:
        base = os.path.basename(p)
        raw = open(p, "rb").read()
        head = raw[:HEAD_BYTES].decode("utf-8", errors="replace")
        full = raw.decode("utf-8-sig", errors="replace")

        if not CHARSET.search(head):
            bad.append("%s : 앞 %d바이트 안에 <meta charset=\"utf-8\"> 이 없다 — 실기에서 한글이 깨진다"
                       % (base, HEAD_BYTES))
        if not VIEWPORT.search(full):
            bad.append("%s : 뷰포트 meta 가 없다 — 모바일이 가상 뷰포트 980px 를 쓴다" % base)
        else:
            if not VP_WIDTH.search(full):
                bad.append("%s : 뷰포트에 width=device-width 가 없다" % base)
            if not VP_COVER.search(full):
                bad.append("%s : 뷰포트에 viewport-fit=cover 가 없다 — safe-area 가 동작하지 않는다" % base)

        # env(safe-area-*) 를 쓰면서 viewport-fit=cover 가 없으면 그 CSS 는 죽은 코드다
        if "safe-area-inset" in full and not VP_COVER.search(full):
            bad.append("%s : safe-area-inset 을 쓰는데 viewport-fit=cover 가 없다" % base)

    if bad:
        return {"status": "fail", "detail": bad}
    return {"status": "ok", "detail": ["게임 %d개 선언 통과" % len(games)]}
