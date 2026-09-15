# -*- coding: utf-8 -*-
"""스코프 상한 검사 — canon/10-scope.md 의 상한을 게임 HTML이 넘지 않는지.

게임 HTML이 지켜야 할 약속(이 형식이어야 셀 수 있다):
    const WEAPON_TYPES = [ { id: 'pipe', ... }, ... ];
    const STATS        = [ { id: 'atk',  ... }, ... ];
    const ZONE_COUNT   = 10;
    const TIER_MAX     = 3;
    const MAX_ONSCREEN_ZOMBIES = 8;

2026-09-08 개정: 오토배틀러 어휘(UNIT_TYPES/WAVE_COUNT/STAR_MAX)에서
방치형 어휘로 교체. 지시 #8·#9.
"""
NAME = "스코프 상한 (canon/10-scope.md 의 값 — 숫자를 여기 적지 않는다. 18차·M2 에서 두 번 낡았다)"
PRIORITY = 1

import io, os, re, glob

LIMIT_RE = re.compile(r"^\s*(SCOPE_MAX_[A-Z_]+)\s*=\s*(\d+)\s*$", re.M)

# 배열 선언 이름 -> 상한 키
ARRAYS = {
    "WEAPON_TYPES": "SCOPE_MAX_WEAPON_TYPES",
    "STATS": "SCOPE_MAX_STATS",
    "GEAR_SLOTS": "SCOPE_MAX_GEAR_SLOTS",      # M4 3: 장비 부위
}
# 정수 상수 이름 -> 상한 키
SCALARS = {
    "ZONE_COUNT": "SCOPE_MAX_ZONES",
    "TIER_MAX": "SCOPE_MAX_TIER",
    "MAX_ONSCREEN_ZOMBIES": "SCOPE_MAX_ONSCREEN_ZOMBIES",
    "GEAR_SHAPES": "SCOPE_MAX_GEAR_SHAPES",    # M4 3: 부위별 방어구 모양
    "GEAR_AFFIXES": "SCOPE_MAX_GEAR_AFFIXES",  # M4 3: 장비 랜덤 옵션 줄 수
}

# **없어도 되는 선언.** 상한은 "넘지 마라" 지 "반드시 있어라" 가 아니다.
# 2026-09-15 M4 3.2 에서 장비 상한 셋을 더했다가 c17 이 잡았다 —
# M1·M2 본보기에는 이 선언이 없어서 검사가 **사람이 "좋다" 로 판정한 산출물을 떨어뜨렸다.**
# 불변 원칙 5: 그때는 산출물이 아니라 **검사를 의심한다.**
# 없으면 0개로 보고 넘어간다. 있으면 상한과 견준다.
OPTIONAL = {"GEAR_SLOTS", "GEAR_SHAPES", "GEAR_AFFIXES"}


def read_limits(root):
    p = os.path.join(root, "canon", "10-scope.md")
    if not os.path.exists(p):
        return None
    with io.open(p, encoding="utf-8") as f:
        txt = f.read()
    return {m.group(1): int(m.group(2)) for m in LIMIT_RE.finditer(txt)}


def count_ids(txt, name):
    """배열 선언을 괄호 짝으로 잘라내고 그 안의 id: 개수를 센다."""
    m = re.search(r"\bconst\s+%s\s*=\s*\[" % re.escape(name), txt)
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
        summary = " / ".join("%s=%d" % (k.replace("SCOPE_MAX_", ""), v)
                             for k, v in sorted(limits.items()))
        return {"status": "skip",
                "detail": ["game/*.html 이 아직 없다 — 게임을 만들면 이 검사가 살아난다",
                           "상한: " + summary]}

    bad = []
    for p in games:
        base = os.path.basename(p)
        with io.open(p, encoding="utf-8", errors="replace") as f:
            txt = f.read()

        for name, key in sorted(ARRAYS.items()):
            n = count_ids(txt, name)
            if n is None:
                if name in OPTIONAL:
                    continue                 # 없어도 되는 선언 — 0개로 본다
                bad.append("%s : const %s = [ ... ] 를 못 찾았다 (셀 수 없음)" % (base, name))
            elif n > limits.get(key, 0):
                bad.append("%s : %s %d개 > 상한 %d개" % (base, name, n, limits.get(key, 0)))

        for name, key in sorted(SCALARS.items()):
            m = re.search(r"\bconst\s+%s\s*=\s*(\d+)" % re.escape(name), txt)
            if not m:
                if name in OPTIONAL:
                    continue                 # 없어도 되는 선언 — 0 으로 본다
                bad.append("%s : const %s 선언을 못 찾았다 (셀 수 없음)" % (base, name))
            elif int(m.group(1)) > limits.get(key, 0):
                bad.append("%s : %s=%s > 상한 %d"
                           % (base, name, m.group(1), limits.get(key, 0)))

    if bad:
        bad.append("상한을 늘리려면 instructions-log.md 에 지시를 남기고 사람이 canon/10-scope.md 를 고친다")
        return {"status": "fail", "detail": bad}
    return {"status": "ok", "detail": ["게임 %d개 상한 이내" % len(games)]}
