# -*- coding: utf-8 -*-
"""줄거리·튜토리얼 표(story/story.csv)를 게임 파일에 넣는다 (지시 #188).

story/story.csv 가 **단일 원본**이다 — 사람이 엑셀로 고치고, 이 도구가 `game/index.html` 의
`const STORY_LINES = [...];` 한 줄로 옮긴다. 게임은 이 표에 적힌 줄만 띄운다(없는 키는 조용히 넘어간다).
열: key,who,text (머리줄 고정). 키: intro · hint_stat · after_stat · hint_gacha · after_gacha · hint_quest · after_quest ·
zone<N>(STORY_ZONES 의 구역) · loop2. 빈 text 줄은 빼고 알려 준다.
엑셀이 한글을 깨뜨리지 않게 저장할 때 UTF-8 BOM 을 붙여 둔다.
쓰는 법: python tools/build_story.py
"""
import io, os, re, csv, sys, json

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "game", "index.html")
SRC = os.path.join(ROOT, "story", "story.csv")
TUT = ["intro", "hint_stat", "after_stat", "hint_gacha", "after_gacha", "hint_quest", "after_quest", "loop2"]


def main():
    raw = io.open(SRC, encoding="utf-8-sig").read()
    rows = list(csv.reader(io.StringIO(raw)))
    head, body = rows[0], rows[1:]
    if [h.strip() for h in head] != ["key", "who", "text"]:
        raise SystemExit("머리줄은 key,who,text 여야 한다 — 지금: %s" % head)
    game = io.open(GAME, encoding="utf-8").read()
    zones = [int(x) for x in re.search(r"const STORY_ZONES = \[([^\]]*)\]", game).group(1).split(",")]
    allowed = set(TUT) | {"zone%d" % z for z in zones}
    lines, empty, bad = [], [], []
    for i, r in enumerate(body, start=2):
        if not any(c.strip() for c in r):
            continue
        r = (r + ["", "", ""])[:3]
        key, who, text = (c.strip() for c in r)
        if key not in allowed:
            bad.append("%d행 키 '%s' — 게임이 모르는 키(쓸 수 있는 키: %s)" % (i, key, ", ".join(sorted(allowed))))
            continue
        if not text:
            empty.append("%d행(%s) 글이 비어 빠짐" % (i, key)); continue
        lines.append([key, who, text])
    if bad:
        raise SystemExit("\n".join(bad))
    for e in empty:
        print("  -", e)
    hints = [k for k in ("hint_stat", "hint_gacha", "hint_quest") if not any(l[0] == k for l in lines)]
    if hints:
        print("  - 말풍선 줄이 없는 안내: %s (그 단계는 화살표만 — 글 없이)" % ", ".join(hints))
    line = "const STORY_LINES = %s;" % json.dumps(lines, ensure_ascii=False, separators=(",", ":"))
    old = re.search(r"^const STORY_LINES = .*;$", game, flags=re.M)
    if not old:
        raise SystemExit("game/index.html 에 'const STORY_LINES = ...;' 줄이 없다")
    before = json.loads(old.group(0)[len("const STORY_LINES = "):-1] or "[]")
    game = game[:old.start()] + line + game[old.end():]
    io.open(GAME, "w", encoding="utf-8", newline="").write(game)
    io.open(SRC, "w", encoding="utf-8-sig", newline="").write(raw.replace("\r\n", "\n"))   # 엑셀용 BOM
    keys = sorted({l[0] for l in lines}, key=lambda k: (k not in TUT, TUT.index(k) if k in TUT else int(k[4:])))
    print("넣었다: %d줄 · 키 %d개 (전 %d줄) — %s" % (len(lines), len(keys), len(before), " ".join(keys)))


if __name__ == "__main__":
    main()
