# -*- coding: utf-8 -*-
"""뷰 파일이 원본과 어긋났는지.

문서를 두 곳에 두면 갈라진다. 이 시스템이 막으려는 바로 그 실패다.
그래서 뷰(HTML)에는 원본의 sha256 을 심어 두고, 원본이 바뀌면 여기서 걸린다.

근거: 규약(지시 #10)이지 사례가 아니다 → 2순위. 막지 않고 경고만 한다.
뷰가 실제로 어긋나 문제를 일으킨 사례가 1건이라도 생기면 PRIORITY 를 1로 올린다.

뷰 파일에 이 줄이 있으면 검사 대상이 된다:
    source-sha256: <원본 .md 의 sha256>
같은 이름의 .md 를 원본으로 본다 (wbs-M1.html -> wbs-M1.md).
"""
NAME = "뷰(HTML)가 원본 문서와 어긋났는지"
PRIORITY = 2

import io, os, re, glob, hashlib

TAG = re.compile(r"source-sha256:\s*([0-9a-f]{64})")


def run(root):
    views = sorted(glob.glob(os.path.join(root, "plans", "*.html")))
    if not views:
        return {"status": "skip", "detail": ["plans/*.html 뷰가 없다"]}

    bad = []
    checked = 0
    for p in views:
        base = os.path.basename(p)
        with io.open(p, encoding="utf-8", errors="replace") as f:
            head = f.read(4000)
        m = TAG.search(head)
        if not m:
            bad.append("%s : source-sha256 주석이 없다 (원본을 알 수 없음)" % base)
            continue

        src = os.path.splitext(p)[0] + ".md"
        if not os.path.exists(src):
            bad.append("%s : 원본 %s 이 없다" % (base, os.path.basename(src)))
            continue

        with io.open(src, encoding="utf-8") as f:
            cur = hashlib.sha256(f.read().encode("utf-8")).hexdigest()
        checked += 1
        if cur != m.group(1):
            bad.append("%s : 원본 %s 이 바뀌었다. 뷰를 다시 만들고 sha256 을 갱신하라"
                       % (base, os.path.basename(src)))

    if bad:
        return {"status": "warn", "detail": bad}
    return {"status": "ok", "detail": ["뷰 %d개가 원본과 일치" % checked]}
