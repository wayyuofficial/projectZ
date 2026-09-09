# -*- coding: utf-8 -*-
"""예측 문구를 결과를 보고 고쳤는지.

근거: 4차 감사 적발. `plans/GAMEDESIGN.md` 예측표에서
  - B2 문구를 "구역 6·8·10 에서 막힌다" → "벽이 생긴다 (예측 위치 6·8·10)" 로 고치고
    판정을 "부분 성립" → "성립" 으로 올렸다
  - B3 의 "반증" 기록을 표에서 지웠다

검사 c4 는 반증 조건 칸의 **존재**만 본다. 사후 문구 수정은 못 잡는다.
그래서 예측 문구와 반증 조건을 `plans/predictions-lock.json` 에 잠그고 여기서 대조한다.

**1순위다.** 예측을 결과에 맞춰 고치면 그건 예측이 아니다 (불변 원칙 3).
예측을 정말 바꿔야 하면 잠금 파일을 사람이 고치고 사유를 남긴다.

## 이 검사가 못 막는 것 (숨기지 않는다)
**잠금 파일과 문서를 함께 고치면 통과한다.** 해시가 잠금 자신의 문구에서 계산되므로
바깥 기준점이 없다. 진짜 기준점은 **git 이력과 사람**이다.
이 검사가 막는 것은 "문서만 몰래 고치기"와 "판정만 몰래 올리기" 두 가지다.
잠금 파일이 바뀌면 git diff 에 남으므로 사람이 볼 수 있다 — 그 이상은 코드로 못 막는다.
"""
NAME = "예측 문구를 결과 보고 고쳤는지"
PRIORITY = 1

import io, os, json, hashlib


def h(t):
    return hashlib.sha256(t.encode("utf-8")).hexdigest()[:16]


def norm(t):
    return " ".join(t.replace("**", "").split())


def run(root):
    lock_p = os.path.join(root, "plans", "predictions-lock.json")
    doc_p = os.path.join(root, "plans", "GAMEDESIGN.md")
    if not os.path.exists(lock_p):
        return {"status": "skip", "detail": ["plans/predictions-lock.json 이 없다"]}
    if not os.path.exists(doc_p):
        return {"status": "fail", "detail": ["plans/GAMEDESIGN.md 가 없다"]}

    try:
        lock = json.load(io.open(lock_p, encoding="utf-8"))
    except Exception as e:
        return {"status": "error", "detail": ["잠금 파일을 못 읽었다: %s" % e]}

    with io.open(doc_p, encoding="utf-8", errors="replace") as f:
        doc = f.read()

    bad = []
    for p in lock.get("예측", []):
        pid = p.get("id", "?")
        # 잠금 파일 자체가 손대졌는지
        if h(p.get("예측", "")) != p.get("예측해시") or h(p.get("반증조건", "")) != p.get("반증해시"):
            bad.append("%s : 잠금 파일 안에서 문구와 해시가 어긋난다 (잠금이 손대졌다)" % pid)
            continue
        # 문서에 원문이 그대로 살아 있는지
        if norm(p["예측"]) not in norm(doc):
            bad.append("%s : 잠근 예측 문구가 GAMEDESIGN.md 에 없다 — 결과를 보고 고쳤는가? [%s]"
                       % (pid, p["예측"][:40]))
        if norm(p["반증조건"]) not in norm(doc):
            bad.append("%s : 잠근 반증 조건이 GAMEDESIGN.md 에 없다 [%s]"
                       % (pid, p["반증조건"][:40]))
        # 판정도 대조한다. 문구를 그대로 두고 판정만 올리는 수법을 막는다.
        # **칸 단위로 정확히 비교한다.** 부분 문자열로 비교하면 "성립" 이 "부분 성립" 안에 들어 있어
        # 부분 성립 → 성립 으로 올려도 통과한다 (2026-09-09 6차 감사가 이 구멍을 뚫었다).
        if h(p.get("판정", "")) != p.get("판정해시"):
            bad.append("%s : 잠금 파일 안에서 판정과 해시가 어긋난다 (잠금이 손대졌다)" % pid)
            continue
        # 같은 id 의 행이 여럿이면 미끼 행을 앞에 끼워 넣는 수법이 통한다 (7차 감사가 뚫었다)
        rows = []
        for line in doc.splitlines():
            cells = [c.strip() for c in line.split("|")]
            if len(cells) > 2 and cells[1].replace("*", "").strip() == pid:
                rows.append(cells)
        if not rows:
            bad.append("%s : GAMEDESIGN.md 예측표에서 이 항목의 행을 못 찾았다" % pid)
        elif len(rows) > 1:
            bad.append("%s : 같은 id 의 행이 %d개다 — 미끼 행을 끼워 넣었는가?" % (pid, len(rows)))
        else:
            want = norm(p.get("판정", ""))
            # **결과 칸(마지막 칸)만** 본다. 행 안의 아무 칸이나 보면
            # 실측 칸에 "부분 성립" 을 적어두고 결과 칸을 "성립" 으로 올리는 수법이 통한다
            # (7차 감사가 이 구멍을 뚫었다).
            cells = [c for c in rows[0] if c != ""]
            verdict = cells[-1] if cells else ""
            # 판정 칸은 "**부분 성립** — 설명…" 처럼 설명이 붙는다. 설명을 떼고 토큰만 비교한다.
            if norm(verdict.split("—")[0]) != want:
                bad.append("%s : 결과 칸이 [%s] 인데 잠근 판정은 [%s] 다 — 판정을 바꿨는가?"
                           % (pid, verdict.split("—")[0].strip()[:20], p.get("판정", "")))

        # 반증된 예측의 기록이 사라졌는지
        if p.get("판정") == "반증" and "반증" not in doc:
            bad.append("%s : 반증된 예측인데 문서에 반증 기록이 없다" % pid)

    if bad:
        bad.append("예측을 정말 바꿔야 하면 plans/predictions-lock.json 을 사람이 고치고 사유를 남긴다")
        return {"status": "fail", "detail": bad}
    return {"status": "ok", "detail": ["예측 %d개 문구가 잠근 그대로" % len(lock.get("예측", []))]}
