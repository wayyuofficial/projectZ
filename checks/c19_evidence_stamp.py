# -*- coding: utf-8 -*-
"""지금 서 있는 판정이 인용하는 측정 기록이 **현재 빌드**의 것인지.

근거: rules/R005-근거는현물.md (사례 16·17·18 — 같은 뿌리 3회)

`c9_measurement_freshness` 는 `balance-*.json` **전체에서 가장 새 파일 하나**의 시각만 본다.
그래서 곡선 기록이 새로우면 그 뒤에 숨은 부스트 기록이 네 빌드 전이어도 초록이었다 (사례 18).
이 검사는 **시각이 아니라 빌드도장**을, **파일 하나가 아니라 인용된 것 전부**를 본다.

## 무엇을 근거로 보는가
- `plans/predictions-lock.json` 의 `판정이력[-1].근거` — **마지막** 판정의 근거.
  지난 이력은 역사지 지금 서 있는 판정이 아니다 (처음엔 전부 훑어 거짓 경고를 냈다).
- `plans/wbs-*.md` 의 본문에 백틱으로 적힌 `*.json` — 작업 완료 판정의 근거

## 빠져나가는 길 (막지 않고 적게 한다)
옛 빌드 기록을 그대로 근거로 쓸 이유가 있으면 그 기록 안에 `옛빌드_사유` 한 줄을 적는다.
그러면 이 검사가 통과시키고 그 이유를 출력한다. **적을 말이 없으면 다시 재는 게 맞다** (R005-4).

## 이 검사가 못 막는 것 (숨기지 않는다)
- 도장이 같아도 값이 틀릴 수 있다. 그건 R002·c16 의 몫이다.
- 인용을 아예 안 한 판정은 볼 수 없다. 근거 칸에 파일명이 없으면 이 검사에 안 걸린다.
"""
NAME = "판정 근거 기록이 현재 빌드의 것인지"
PRIORITY = 1

import io, os, re, json, glob, hashlib

JSON_RE = re.compile(r"[A-Za-z0-9_\-.]+\.json")


def _stamp(path):
    raw = open(path, "rb").read()
    return (hashlib.sha256(raw).hexdigest()[:16],
            hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()[:16])


def _cited(root):
    """(파일명, 어디서 인용했는지) 목록."""
    out = []
    lock = os.path.join(root, "plans", "predictions-lock.json")
    if os.path.exists(lock):
        try:
            d = json.load(io.open(lock, encoding="utf-8"))
            for p in d.get("예측", []):
                hist = p.get("판정이력", []) or []
                if hist:                       # 지금 서 있는 판정 = 마지막 이력 하나.
                    for m in JSON_RE.findall(str(hist[-1].get("근거", ""))):
                        out.append((m, "예측 %s 판정근거" % p.get("id")))
        except Exception:
            pass
    for w in sorted(glob.glob(os.path.join(root, "plans", "wbs-*.md"))):
        try:
            for m in JSON_RE.findall(io.open(w, encoding="utf-8").read()):
                out.append((m, os.path.basename(w)))
        except Exception:
            pass
    return out


def run(root):
    games = sorted(glob.glob(os.path.join(root, "game", "*.html")))
    if not games:
        return {"status": "skip", "detail": ["game/*.html 이 없다"]}
    now, shown = set(), None
    for g in games:
        raw, lf = _stamp(g)
        now.update((raw, lf))
        if shown is None:
            shown = raw

    index = {}
    for p in glob.glob(os.path.join(root, "measurements", "**", "*.json"), recursive=True):
        index.setdefault(os.path.basename(p), p)

    cited = _cited(root)
    if not cited:
        return {"status": "ok", "detail": ["판정 근거로 인용된 측정 기록이 없다"]}

    bad, okd, seen = [], [], set()
    for name, where in cited:
        if name in seen:
            continue
        seen.add(name)
        path = index.get(name)
        if not path:
            bad.append("%s 가 %s 에서 근거로 인용됐는데 measurements/ 에 없다" % (name, where))
            continue
        try:
            rec = json.load(io.open(path, encoding="utf-8"))
        except Exception as e:
            bad.append("%s 를 읽지 못했다 (%s)" % (name, e))
            continue
        st = rec.get("빌드도장")
        if not st:
            continue                      # 빌드와 무관한 기록
        if st in now:
            okd.append(name)
            continue
        why = rec.get("옛빌드_사유")
        if why:
            okd.append("%s (옛 빌드, 사유: %s)" % (name, why))
            continue
        bad.append("%s — %s 의 근거인데 도장이 %s 다. 현재 빌드는 %s. 다시 재거나 기록에 [옛빌드_사유] 를 적어라 (R005)"
                   % (name, where, st, shown))

    if bad:
        return {"status": "warn", "detail": bad}
    return {"status": "ok", "detail": ["근거 기록 %d개 전부 현재 빌드: %s" % (len(okd), ", ".join(okd[:4]) + (" 외" if len(okd) > 4 else ""))]}
