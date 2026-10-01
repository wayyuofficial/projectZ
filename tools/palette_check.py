# -*- coding: utf-8 -*-
"""그리기 코드에 직접 쓴 색이 몇 개인지 — M5 1.1 완료 판정.

색은 `const PALETTE = { ... }` 한 곳에만 둔다. 데이터 표(WEAPON_TYPES 의 tint 같은 **내용** 색)는 빼고 센다 —
그건 무기의 정체성이지 화면 톤이 아니다. 나머지 자리에 `#RRGGBB` · `rgba(...)` 가 직접 있으면 센다.

쓰는 법:
    python tools/palette_check.py            # 개수와 자리
    python tools/palette_check.py --out measurements/palette-YYYY-MM-DD.json
"""
import io, os, re, sys, json, argparse, hashlib, datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "game", "index.html")

TABLES = ("WEAPON_TYPES", "STATS", "GEAR_SLOTS", "AFFIX_DEFS", "QUEST_POOL", "QUEST_SLOTS", "PALETTE")
COLOR = re.compile(r"#[0-9A-Fa-f]{6}\b|#[0-9A-Fa-f]{3}\b|rgba?\(\s*\d")   # rgba( 뒤에 숫자가 바로 올 때만 리터럴이다 — 'rgba(' + PALETTE.deathRgb 는 색이 PALETTE 에서 온다 (1.1 오탐 1건)


def scan():
    src = io.open(GAME, encoding="utf-8-sig").read().split("\n")
    hits, in_tbl, fn, in_script = [], None, "", False
    in_block = False
    for n, line in enumerate(src, 1):
        # <script> 앞의 CSS·HTML 은 그리기 코드가 아니다 — JS 상수를 못 읽는 자리라 여기 색은 따로 둔다
        if "<script" in line:
            in_script = True
        if not in_script:
            continue
        m = re.match(r"^function\s+(\w+)", line)
        if m:
            fn = m.group(1)
        t = re.match(r"^const\s+(\w+)\s*=\s*[\[{]", line)
        if t and t.group(1) in TABLES:
            in_tbl = t.group(1)
        if in_tbl:
            if re.match(r"^[\]}];", line):
                in_tbl = None
            continue
        # 주석 줄의 색은 안 센다 (설명용). 2026-09-30: 여러 줄 주석(/* ... */) 안의 이어지는 줄도 — 사례 25 와 같은 오탐('지시 #127' 의 #127)
        st = line.strip()
        if in_block:
            if "*/" in st:
                in_block = False
            continue
        if st.startswith("/*") and "*/" not in st:
            in_block = True; continue
        if st.startswith(("//", "/*", "*")):
            continue
        # 줄 중간에서 시작해 다음 줄로 이어지는 블록 주석(`const X = 1;   /* 설명 ...` + 다음 줄) — 2026-09-30 세 번째 오탐: ZONE_HP_G 주석 둘째 줄의 '#139'
        if "/*" in line and "*/" not in line[line.index("/*"):]:
            line = line[:line.index("/*")]; in_block = True
        elif "/*" in line and "*/" in line:
            line = re.sub(r"/\*.*?\*/", "", line)
        # 줄 끝 주석(// ...)도 안 센다 — 2026-09-18 오탐: "// 지시 #118" 의 '#118' 이 3자리 hex 로 잡혔다 (등급명 빌드 b503e5adadd6a324)
        line = line.split("//")[0] if "//" in line and "://" not in line else line
        for c in COLOR.finditer(line):
            hits.append({"줄": n, "함수": fn, "색": line[c.start():c.start() + 24].split(")")[0] + (")" if "(" in line[c.start():c.start() + 6] else ""), "본문": line.strip()[:80]})
    return hits


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    a = ap.parse_args(argv[1:])
    hits = scan()
    by_fn = {}
    for h in hits:
        by_fn[h["함수"]] = by_fn.get(h["함수"], 0) + 1
    print("PALETTE·데이터 표 밖에 직접 쓴 색: %d개" % len(hits))
    for fn, n in sorted(by_fn.items(), key=lambda x: -x[1]):
        print("  %3d  %s" % (n, fn or "(전역)"))
    ok = len(hits) == 0
    print("1.1 완료 판정(0개): %s" % ("통과" if ok else "**미달**"))
    if a.out:
        stamp = hashlib.sha256(io.open(GAME, "rb").read()).hexdigest()[:16]
        io.open(a.out, "w", encoding="utf-8").write(json.dumps(
            {"측정일": datetime.date.today().isoformat(), "도구": "tools/palette_check.py", "빌드도장": stamp,
             "직접_쓴_색": len(hits), "함수별": by_fn, "자리": hits, "제외한_표": list(TABLES),
             "결과": "통과" if ok else "미달", "판정하지_않는다": "판정은 검증자·사람 몫이다."}, ensure_ascii=False, indent=2))
        print("기록:", a.out)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
