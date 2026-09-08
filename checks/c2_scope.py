# -*- coding: utf-8 -*-
"""스코프 상한 검사 — canon/10-scope.md 의 상한을 게임 HTML이 넘지 않는지.

게임 HTML이 지켜야 할 약속(이 형식이어야 셀 수 있다):
    const UNIT_TYPES = [ { id: 'knight', ... }, ... ];
    const WAVE_COUNT = 10;
    const STAR_MAX = 3;
"""
NAME = "스코프 상한 (유닛 6 / 웨이브 10 / 별 3)"
PRIORITY = 1

import io, os, re, glob

LIMIT_RE = re.compile(r"^\s*(SCOPE_MAX_[A-Z_]+)\s*=\s*(\d+)\s*$", re.M)
INT_RE = {
    "waves": re.compile(r"\bconst\s+WAVE_COUNT\s*=\s*(\d+)"),
    "star": re.compile(r"\bconst\s+STAR_MAX\s*=\s*(\d+)"),
}


def read_limits(root):
    p = os.path.join(root, "canon", "10-scope.md")
    if not os.path.exists(p):
        return None
    with io.open(p, encoding="utf-8") as f:
        txt = f.read()
    return {m.group(1): int(m.group(2)) for m in LIMIT_RE.finditer(txt)}


def count_units(txt):
    """UNIT_TYPES 배열을 괄호 짝으로 잘라내고 그 안의 id: 개수를 센다."""
    m = re.search(r"\bconst\s+UNIT_TYPES\s*=\s*\[", txt)
    if not m:
        return None
    i = m.end() - 1
    depth = 0
    for j in range(i, len(txt)):
        if txt[j] == "[":
            depth += 1
        elif txt[j] == "]":
            depth -= 1
            if depth == 0:
                return len(re.findall(r"\bid\s*:", txt[i:j]))
    return None


def run(root):
    limits = read_limits(root)
    if not limits:
        return {"status": "error", "detail": ["canon/10-scope.md 에서 상한을 못 읽었다"]}

    games = sorted(glob.glob(os.path.join(root, "game", "*.html")))
    if not games:
        return {"status": "skip",
                "detail": ["game/*.html 이 아직 없다 — 게임을 만들면 이 검사가 살아난다",
                           "상한: 유닛 %d / 웨이브 %d / 별 %d"
                           % (limits.get("SCOPE_MAX_UNIT_TYPES", -1),
                              limits.get("SCOPE_MAX_WAVES", -1),
                              limits.get("SCOPE_MAX_STAR", -1))]}

    bad = []
    for p in games:
        base = os.path.basename(p)
        with io.open(p, encoding="utf-8", errors="replace") as f:
            txt = f.read()

        n = count_units(txt)
        if n is None:
            bad.append("%s : const UNIT_TYPES = [ ... ] 를 못 찾았다 (셀 수 없음)" % base)
        elif n > limits.get("SCOPE_MAX_UNIT_TYPES", 6):
            bad.append("%s : 유닛 %d종 > 상한 %d종"
                       % (base, n, limits["SCOPE_MAX_UNIT_TYPES"]))

        for key, rx in INT_RE.items():
            mm = rx.search(txt)
            limit_key = "SCOPE_MAX_WAVES" if key == "waves" else "SCOPE_MAX_STAR"
            if not mm:
                bad.append("%s : %s 선언을 못 찾았다 (셀 수 없음)"
                           % (base, "WAVE_COUNT" if key == "waves" else "STAR_MAX"))
            elif int(mm.group(1)) > limits.get(limit_key, 99):
                bad.append("%s : %s=%s > 상한 %d"
                           % (base, key, mm.group(1), limits[limit_key]))

    if bad:
        bad.append("상한을 늘리려면 instructions-log.md 에 지시를 남기고 사람이 canon/10-scope.md 를 고친다")
        return {"status": "fail", "detail": bad}
    return {"status": "ok", "detail": ["게임 %d개 상한 이내" % len(games)]}
