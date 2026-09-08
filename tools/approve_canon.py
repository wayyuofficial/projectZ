# -*- coding: utf-8 -*-
"""정본 변경을 사람이 승인했다고 기록한다.

**사람이 직접 실행하는 도구다.** AI는 실행하지 않는다.
canon/*.md 의 현재 해시를 measurements/canon-hashes.json 에 새로 적는다.
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

    h = {}
    for p in files:
        with io.open(p, "rb") as f:
            h[os.path.basename(p)] = hashlib.sha256(f.read()).hexdigest()

    out = os.path.join(ROOT, "measurements", "canon-hashes.json")
    with io.open(out, "w", encoding="utf-8") as f:
        json.dump({"approved_at": datetime.datetime.now().isoformat(timespec="seconds"),
                   "note": "사람이 승인한 정본 상태. AI가 이 파일을 갱신하면 감시가 무의미해진다.",
                   "hashes": h}, f, ensure_ascii=False, indent=2)

    print("정본 %d개 승인 기록: %s" % (len(h), out))
    for k in h:
        print("  %s" % k)
    return 0


if __name__ == "__main__":
    sys.exit(main())
