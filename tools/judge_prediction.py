# -*- coding: utf-8 -*-
"""예측 잠금(plans/predictions-lock.json)의 **판정**을 사람이 바꿨다고 기록한다.

**사람이 직접 실행하는 도구다. AI는 실행하지 않는다.**

## 왜 이 도구가 있는가 (2026-09-10 15차 감사)

예측 문구·반증 조건·판정은 `plans/predictions-lock.json` 에 잠겨 있고
`checks/c15_prediction_lock.py` 가 문서(`plans/GAMEDESIGN.md`)와 대조한다.
그런데 c15 는 **잠금과 문서가 서로 같은지**만 본다. 판정이 게임에서 참인지는 못 본다.

B2("구역 6·8·10 에서 막힌다")의 반증 조건은 "아무 데서도 10분 이상 안 막히면 실패" 인데
14차·15차 감사가 20시드에서 벽이 0개라고 두 번 확인했다. **B2 는 반증이다.**
그런데 잠금의 판정은 "부분 성립" 그대로였고, c15 는 그것을 [ OK ] 로 인증했다.
"잠금은 사람이 고친다" 고 적어 두고 아무도 고치지 않으면 **틀린 판정이 검사의 보호를 받는다.**

그래서 이 도구는 `approve_canon.py` 와 같은 방식으로:
1. **사람이 이름을 타이핑해야 한다.** 입력이 터미널이 아니면 거부한다.
2. 판정을 바꾼 사람·시각·근거를 잠금 파일 안 `판정이력` 에 남긴다.
3. **문구와 반증 조건은 건드리지 않는다.** 바꿀 수 있는 것은 판정 하나다 — 예측을 결과에 맞춰
   고치는 것은 이 도구로도 못 한다(불변 원칙 3).
4. `plans/GAMEDESIGN.md` 예측표의 **결과 칸**을 같이 맞춘다. c15 가 둘을 대조하기 때문이다.

쓰는 법:
    python tools/judge_prediction.py B2 반증
그리고 이름과 근거를 묻는 대로 적는다. 판정은 `성립` / `부분 성립` / `반증` 중 하나다.
"""
import io, os, re, sys, json, hashlib, datetime

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCK = os.path.join(ROOT, "plans", "predictions-lock.json")
DOC = os.path.join(ROOT, "plans", "GAMEDESIGN.md")
ALLOWED = ("성립", "부분 성립", "반증")


def h(t):
    return hashlib.sha256(t.encode("utf-8")).hexdigest()[:16]


def main(argv):
    if len(argv) != 3 or argv[2] not in ALLOWED:
        print("쓰는 법: python tools/judge_prediction.py <예측id> <성립|부분 성립|반증>")
        return 1
    pid, verdict = argv[1], argv[2]

    lock = json.load(io.open(LOCK, encoding="utf-8"))
    rows = [p for p in lock.get("예측", []) if p.get("id") == pid]
    if len(rows) != 1:
        print("잠금 파일에 id %s 가 %d개다. 중단." % (pid, len(rows)))
        return 1
    p = rows[0]
    if h(p["예측"]) != p["예측해시"] or h(p["반증조건"]) != p["반증해시"] or h(p["판정"]) != p["판정해시"]:
        print("잠금 파일 안에서 문구와 해시가 어긋난다 — 이미 손대졌다. 중단. 먼저 c15 를 봐라.")
        return 1

    is_tty = False
    try:
        is_tty = sys.stdin.isatty()
    except Exception:
        pass

    print("예측 판정 변경 — %s" % pid)
    print("  예측     : %s" % p["예측"])
    print("  반증조건 : %s" % p["반증조건"])
    print("  판정     : %s  →  %s" % (p["판정"], verdict))
    print()
    if not is_tty:
        print("거부: 입력이 터미널이 아니다. **이 도구는 사람이 직접 실행한다.**")
        return 2
    if p["판정"] == verdict:
        print("이미 그 판정이다. 아무것도 바꾸지 않았다.")
        return 0

    try:
        who = input("판정하는 사람의 이름을 적는다 (빈 줄이면 중단): ").strip()
        why = input("근거를 한 줄로 적는다 (측정 파일 이름 등. 빈 줄이면 중단): ").strip() if who else ""
    except (EOFError, KeyboardInterrupt):
        print("\n중단했다. 아무것도 바꾸지 않았다.")
        return 2
    if not who or not why:
        print("이름이나 근거가 비었다. 중단했다. 아무것도 바꾸지 않았다.")
        return 2

    # 1) 문서의 결과 칸을 먼저 고친다 — 못 찾으면 잠금도 안 건드린다
    doc = io.open(DOC, encoding="utf-8").read()
    lines = doc.split("\n")
    hit = [i for i, ln in enumerate(lines)
           if len(ln.split("|")) > 2 and ln.split("|")[1].strip().replace("*", "") == pid]
    if len(hit) != 1:
        print("GAMEDESIGN.md 예측표에서 %s 행을 %d개 찾았다. 중단." % (pid, len(hit)))
        return 1
    cells = lines[hit[0]].split("|")
    last = max(i for i, c in enumerate(cells) if c.strip() != "")
    old_cell = cells[last]
    tail = old_cell.split("—", 1)[1].strip() if "—" in old_cell else ""
    note = "%s (%s, %s)" % (why, who, datetime.date.today().isoformat())
    cells[last] = " **%s** — %s%s " % (verdict, note, (" · 이전: " + tail) if tail else "")
    lines[hit[0]] = "|".join(cells)

    # 2) 잠금
    prev = p["판정"]
    p["판정"] = verdict
    p["판정해시"] = h(verdict)
    p.setdefault("판정이력", []).append({
        "시각": datetime.datetime.now().isoformat(timespec="seconds"),
        "판정한_사람": who, "이전": prev, "이후": verdict, "근거": why, "stdin_is_tty": is_tty})

    io.open(DOC, "w", encoding="utf-8").write("\n".join(lines))
    io.open(LOCK, "w", encoding="utf-8").write(json.dumps(lock, ensure_ascii=False, indent=2) + "\n")
    print("기록했다: %s 판정 %s → %s (%s). 잠금과 GAMEDESIGN.md 결과 칸을 함께 바꿨다." % (pid, prev, verdict, who))
    print("다음: python checks/run.py 로 c15 가 [ OK ] 인지 보고, git 에 커밋한다.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
