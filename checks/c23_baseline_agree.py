# -*- coding: utf-8 -*-
"""도구마다 낸 **기준선**이 서로 맞는지 — 자를 보는 두 번째 검사 (R008).

`sell_share` · `focus_check` · `axis_value` 는 전부 같은 `auto_run` 으로 "아무것도 안 건드린 진행" 을
기준선으로 재고 시작한다. 같은 빌드 도장, 같은 시드면 그 값은 **같아야 한다.** 다르면 어느 한 도구가
자기만의 상태로 돌고 있다는 뜻이다.

2026-09-17 에 실제로 그랬다. `axis_value` 가 `--gear-only` 옵션이 없을 때 `GEAR_ONLY_STATS = set()` 으로
원본의 gearOnly 를 **지워 버려**, 포트가 hp·reg 를 다시 사고 기준이 228.9분이 됐다. 같은 도장·같은 20시드의
`sell_share` 는 155.5분이었다. 헛돈틱은 0 이라 c22 는 조용했다 — **실제로 샀으니까.** 그래서 이 검사다.
같은 부류(고르는 줄과 거부 줄이 어긋남)의 세 번째다 (cases/2026-09-16-22, -23).

무엇을 보는가: `measurements/` 에서 빌드도장과 시드 목록이 같은 기록들을 묶고, 기준 도달분이
서로 2% 넘게 벌어지면 경고. 같은 함수·같은 시드면 **동일**해야 하므로 2% 는 넉넉한 값이다.
"""
NAME = "같은 도장·같은 시드에서 도구들의 기준선이 서로 맞는지 (자를 본다)"
PRIORITY = 1

import io, os, glob, json

# 기록 종류 -> (파일 패턴, 기준 도달분 칸)
SOURCES = [
    ("sell-share-*.json", "구역30_도달_중앙_분"),
    ("focus-*.json", "안누름_분"),
    ("axis-value-*.json", "기준_도달분"),
]
TOL = 0.02


def run(root):
    mdir = os.path.join(root, "measurements")
    groups = {}          # (도장, 시드튜플) -> [(파일, 값)]
    n = 0
    for pat, field in SOURCES:
        for p in sorted(glob.glob(os.path.join(mdir, pat))):
            base = os.path.basename(p)
            if "gearonly" in base or "_selftest" in base and False:
                continue                     # 장비 전용 실험은 조건이 달라 기준선이 다른 게 맞다
            try:
                d = json.load(io.open(p, encoding="utf-8"))
            except Exception:
                continue
            stamp, seeds, val = d.get("빌드도장"), d.get("시드"), d.get(field)
            if not stamp or not seeds or not isinstance(val, (int, float)):
                continue
            n += 1
            groups.setdefault((stamp, tuple(seeds)), []).append((base, float(val)))

    bad, checked = [], 0
    for (stamp, seeds), rows in sorted(groups.items()):
        if len(rows) < 2:
            continue
        checked += 1
        vals = [v for _, v in rows]
        lo, hi = min(vals), max(vals)
        if lo > 0 and (hi - lo) / lo > TOL:
            bad.append("도장 %s · %d시드 — 기준선이 %.1f%% 벌어졌다: %s. 같은 auto_run 인데 다르면 어느 도구가 자기만의 상태로 돈다 (R008)"
                       % (stamp, len(seeds), (hi - lo) / lo * 100,
                          ", ".join("%s=%.1f분" % (b, v) for b, v in rows)))
    if not n:
        return {"status": "skip", "detail": ["기준선을 가진 기록이 없다"]}
    if bad:
        return {"status": "warn", "detail": bad}
    return {"status": "ok", "detail": ["기록 %d개 · 같은 도장·시드 묶음 %d개의 기준선이 2%% 안에서 일치" % (n, checked)]}
