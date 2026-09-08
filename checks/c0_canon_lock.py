# -*- coding: utf-8 -*-
"""정본이 승인 없이 바뀌었는지 해시로 감시한다.

한계를 숨기지 않는다: 이 검사는 변경을 **막지 못하고 드러낼 뿐이다.**
진짜 되돌리기 수단은 git 이력이다.
"""
NAME = "정본이 승인 없이 바뀌었는지"
PRIORITY = 1

import io, os, json, glob, hashlib


def hashes(root):
    out = {}
    for p in sorted(glob.glob(os.path.join(root, "canon", "*.md"))):
        with io.open(p, "rb") as f:
            out[os.path.basename(p)] = hashlib.sha256(f.read()).hexdigest()
    return out


def run(root):
    man = os.path.join(root, "measurements", "canon-hashes.json")
    cur = hashes(root)
    if not cur:
        return {"status": "error", "detail": ["canon/*.md 가 하나도 없다"]}
    if not os.path.exists(man):
        return {"status": "error",
                "detail": ["해시 대장이 없다: measurements/canon-hashes.json",
                           "python tools/approve_canon.py 로 만든다"]}
    with io.open(man, encoding="utf-8") as f:
        old = json.load(f).get("hashes", {})

    bad = []
    for k, v in cur.items():
        if k not in old:
            bad.append("새 정본 파일: %s (사람 승인 필요)" % k)
        elif old[k] != v:
            bad.append("정본이 바뀜: %s" % k)
    for k in old:
        if k not in cur:
            bad.append("정본이 사라짐: %s" % k)

    if bad:
        bad.append("사람이 의도한 변경이면 python tools/approve_canon.py 실행")
        return {"status": "fail", "detail": bad}
    return {"status": "ok", "detail": ["정본 %d개 일치" % len(cur)]}
