# -*- coding: utf-8 -*-
"""실기 요청서가 **판정 문구 그대로**였는지 — 기록에 원문이 붙어 있고 그 글자가 WBS 에 실제로 있는지.

근거: rules/R006-요청서는판정문구그대로.md (사례 15·20 — 같은 패턴 2회)

두 번 다 사람은 성실히 답했고 기록도 정직했다. **틀린 것은 물음이었다.**
- 사례 15: 판정 문구의 절 하나를 요청서에서 **뺐다**.
- 사례 20: "처음부터" 를 "이번에" 로 **깎았다** — 구역 15 까지 간 저장 위에서 "구역 10 까지 갔나" 를 물었다.

## 무엇을 보는가
`measurements/device-*.json` 중 **요청 항목을 담은 기록**(키 이름에 '요청' 이 든 것)에 대해:
  1. `판정문구_원문` 칸이 있는가
  2. 그 글자가 `plans/wbs-*.md` 안에 **실제로 있는가** (공백만 무시하고 그대로 대조)

## 이 검사가 못 보는 것 (숨기지 않는다)
**요청 항목이 그 문구를 뜻으로 덮는지는 못 본다.** 문장 의미 비교는 검사의 일이 아니다 —
절차 60 의 단계와 감사 회차의 눈에 맡긴다.
이 검사가 하는 일은 **원문을 옆에 놓게 강제하는 것**까지다. 나란히 놓이면 깎인 자리가 눈에 띈다.
"""
NAME = "실기 요청서가 판정 문구 그대로였는지"
PRIORITY = 1

import io, os, re, json, glob

WS = re.compile(r"\s+")


def _flat(t):
    return WS.sub("", t)


def run(root):
    recs = sorted(glob.glob(os.path.join(root, "measurements", "device-*.json")))
    if not recs:
        return {"status": "skip", "detail": ["measurements/device-*.json 이 없다"]}

    wbs = ""
    for w in sorted(glob.glob(os.path.join(root, "plans", "wbs-*.md"))):
        try:
            wbs += io.open(w, encoding="utf-8").read()
        except Exception:
            pass
    flat_wbs = _flat(wbs)

    bad, okd = [], []
    for p in recs:
        base = os.path.basename(p)
        try:
            d = json.load(io.open(p, encoding="utf-8"))
        except Exception as e:
            bad.append("%s 를 읽지 못했다 (%s)" % (base, e))
            continue
        if not isinstance(d, dict):
            continue
        asked = [k for k in d if "요청" in k]
        if not asked:
            continue                       # 요청 항목이 없는 기록은 이 검사의 대상이 아니다
        src = d.get("판정문구_원문")
        if not src:
            bad.append("%s : 요청 항목(%s)은 있는데 [판정문구_원문] 이 없다 — 판정 문구를 그대로 붙여라 (R006-4)"
                       % (base, asked[0]))
            continue
        for one in (src if isinstance(src, list) else [src]):
            if _flat(str(one)) not in flat_wbs:
                bad.append("%s : [판정문구_원문] 이 plans/wbs-*.md 에 없다 — 요청서가 문구에서 떠내려갔거나 문구가 바뀌었다: %s"
                           % (base, str(one)[:70]))
                break
        else:
            okd.append(base)

    if bad:
        return {"status": "fail", "detail": bad}
    return {"status": "ok", "detail": ["실기 기록 %d개가 판정 문구 원문을 달고 있고 WBS 와 일치: %s" % (len(okd), ", ".join(okd))]}
