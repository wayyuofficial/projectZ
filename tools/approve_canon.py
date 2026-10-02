# -*- coding: utf-8 -*-
"""정본 변경을 사람이 승인했다고 기록한다.

**사람이 직접 실행하는 도구다. AI는 실행하지 않는다.**
canon/*.md 의 현재 해시를 measurements/canon-hashes.json 에 새로 적는다.

## 왜 이름을 묻는가 (2026-09-09 14차 감사)

이 도구는 예전에 시각과 해시만 적었다. 그래서 **AI 가 돌려도 파일이 똑같았다.**
감사가 그것을 이렇게 적었다:

> "사람이 approve_canon.py 를 돌렸다" 가 유일한 사람 개입 증거인데, 그 도구는 시각과 해시만 쓴다.
> AI 가 돌려도 파일이 똑같다. 즉 "문은 사람 쪽에 있다" 는 주장은 **저장소 안에서 반증도 확증도 불가능하다.**
> ... 하지 않으면 "정본은 사람만 고친다" 는 이 저장소의 마지막 방벽이 **말로만 남는다.**

그래서 이제:
1. **사람이 이름을 타이핑해야 한다.** 입력이 없으면(파이프·리다이렉트·자동 실행) **거부하고 멈춘다.**
2. 그 이름과 "입력이 실제 터미널이었는가"(`stdin_is_tty`)를 함께 남긴다.

**이것도 완전한 방벽은 아니다.** 마음먹으면 가짜 터미널로 흉내낼 수 있다.
다만 그렇게 하려면 **의도적으로 여러 단계를 밟아야 하고, 그 흔적이 git 에 남는다.**
이 도구가 막는 것은 "무심코 AI 가 승인 도장을 찍는 것" 하나다. 그 이상은 코드로 못 막는다.
"""
import io, os, sys, json, glob, hashlib, datetime

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    files = sorted(glob.glob(os.path.join(ROOT, "canon", "*.md")))
    if not files:
        print("canon/*.md 가 없다. 중단.")
        return 1

    is_tty = False
    try:
        is_tty = sys.stdin.isatty()
    except Exception:
        pass

    print("정본 승인 — 아래 파일들의 현재 상태를 '사람이 확인했다' 로 기록한다.")
    print("  (먼저 git pull 로 최신 정본을 받았는가? 받기 전에 승인하면 받은 뒤 다시 승인해야 한다 — 2026-10-02)")
    for p in files:
        print("  %s" % os.path.basename(p))
    print()
    if not is_tty:
        print("거부: 입력이 터미널이 아니다. **이 도구는 사람이 직접 실행한다.**")
        print("      자동 실행·파이프·리다이렉트로는 승인하지 않는다.")
        return 2

    try:
        who = input("승인하는 사람의 이름을 적는다 (빈 줄이면 중단): ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n중단했다. 아무것도 바꾸지 않았다.")
        return 2
    if not who:
        print("이름이 비었다. 중단했다. 아무것도 바꾸지 않았다.")
        return 2

    h = {}
    for p in files:
        with io.open(p, "rb") as f:
            h[os.path.basename(p)] = hashlib.sha256(f.read()).hexdigest()

    out = os.path.join(ROOT, "measurements", "canon-hashes.json")
    prev = {}
    if os.path.exists(out):
        try:
            prev = json.load(io.open(out, encoding="utf-8")).get("hashes", {})
        except Exception:
            prev = {}
    changed = sorted(k for k in h if prev.get(k) != h[k])

    with io.open(out, "w", encoding="utf-8") as f:
        json.dump({"approved_at": datetime.datetime.now().isoformat(timespec="seconds"),
                   "approved_by": who,
                   "stdin_is_tty": is_tty,
                   "changed_since_last": changed,
                   "note": "사람이 승인한 정본 상태. AI가 이 파일을 갱신하면 감시가 무의미해진다. "
                           "approved_by 는 사람이 직접 타이핑한 값이다 — 터미널이 아니면 도구가 거부한다.",
                   "hashes": h}, f, ensure_ascii=False, indent=2)

    print()
    print("정본 %d개 승인 기록: %s" % (len(h), out))
    print("  승인자: %s" % who)
    if changed:
        print("  지난 승인 이후 바뀐 것: %s" % ", ".join(changed))
    else:
        print("  지난 승인 이후 바뀐 것: 없음")
    return 0


if __name__ == "__main__":
    sys.exit(main())
