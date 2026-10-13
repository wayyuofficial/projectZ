# -*- coding: utf-8 -*-
"""게임 파일 안의 그림(data URI)을 game/img/ 파일로 빼고 경로만 남긴다 (M25, 지시 #190).

왜: 그림을 data URI 로 넣으면 game/index.html 이 그만큼 커진다(c27 상한 5MB). 폰 WebView 는 이 파일을 통째로 읽는다.
그림은 `new Image(); im.src = …` 로 읽으므로 data URI 든 경로든 코드가 같다 — 문자열만 바꾸면 된다.
소리(data:audio)는 빼지 않는다 — 파일에서 읽으려면 fetch 가 필요한데 c3(서버 통신 금지)가 막는다.

쓰는 법 — 그림 만드는 도구(build_ui · embed_zones · build_fx · build_weapons · build_hero_video · sheet_tools)를 돌린 **뒤에** 한 번:
    python tools/externalize_art.py            # 빼기 + 안 쓰는 파일 지우기
    python tools/externalize_art.py --check    # 바꾸지 않고 상태만(빠진 그림·없는 파일·남은 파일)

이름: img/<그림이 든 상수 이름>-<내용 해시 10자>.<확장자>. 같은 그림은 같은 이름이라 두 번 돌려도 그대로다.
"""
import io, os, re, sys, base64, hashlib, argparse

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "game", "index.html")
IMG_DIR = os.path.join(ROOT, "game", "img")
URI = re.compile(r"data:image/(webp|png|jpeg|gif);base64,([A-Za-z0-9+/=]+)")
REF = re.compile(r"""['"](img/[A-Za-z0-9_.\-]+)['"]""")
CONST = re.compile(r"(?:const|let|var)\s+(\w+)\s*=")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    txt = io.open(GAME, encoding="utf-8").read()
    before = len(txt.encode("utf-8"))
    out, last, wrote, n = [], 0, 0, 0
    consts = [(m.start(), m.group(1)) for m in CONST.finditer(txt)]
    ci = 0; cur = "ART"
    for m in URI.finditer(txt):
        while ci < len(consts) and consts[ci][0] < m.start():
            cur = consts[ci][1]; ci += 1
        raw = base64.b64decode(m.group(2))
        ext = "jpg" if m.group(1) == "jpeg" else m.group(1)
        name = "%s-%s.%s" % (cur, hashlib.sha256(raw).hexdigest()[:10], ext)
        path = os.path.join(IMG_DIR, name)
        if not a.check and not os.path.exists(path):
            os.makedirs(IMG_DIR, exist_ok=True)
            open(path, "wb").write(raw); wrote += 1
        out.append(txt[last:m.start()]); out.append("img/" + name); last = m.end(); n += 1
    out.append(txt[last:])
    new = "".join(out)
    refs = set(REF.findall(new))
    have = set("img/" + f for f in os.listdir(IMG_DIR)) if os.path.isdir(IMG_DIR) else set()
    missing = sorted(refs - have) if a.check else sorted(r for r in refs if not os.path.exists(os.path.join(ROOT, "game", r)))
    orphan = sorted(have - refs)
    if a.check:
        print("게임 안에 남은 그림 data URI: %d · 경로 %d · 없는 파일 %d · 안 쓰는 파일 %d" % (n, len(refs), len(missing), len(orphan)))
        for r in missing[:10]: print("  없음:", r)
        sys.exit(1 if (n or missing) else 0)
    for r in orphan:
        os.remove(os.path.join(ROOT, "game", r))
    if missing:
        raise SystemExit("경로가 가리키는 파일이 없다: %s" % ", ".join(missing[:10]))
    if new != txt:
        io.open(GAME, "w", encoding="utf-8", newline="").write(new)
    total = sum(os.path.getsize(os.path.join(IMG_DIR, f)) for f in os.listdir(IMG_DIR)) if os.path.isdir(IMG_DIR) else 0
    print("뺐다: 그림 %d개(새 파일 %d · 지운 파일 %d) · 게임 파일 %.2fMB → %.2fMB · img %d개 %.2fMB"
          % (n, wrote, len(orphan), before / 1e6, len(new.encode("utf-8")) / 1e6, len(refs), total / 1e6))


if __name__ == "__main__":
    main()
