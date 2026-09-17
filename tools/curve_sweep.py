# -*- coding: utf-8 -*-
"""상수 후보를 하나씩 게임에 넣어 곡선을 잰다 — 격자 기록을 남기는 저장소 도구.

2026-09-16·17 의 곡선 재조정은 스크래치 스크립트로 격자를 돌리고 숫자만 WBS 에 적었다.
30차 감사가 잡았다: *"8시드 격자 1.62 139분 · 1.63 156분 … 은 measurements/ 에 기록 파일이 없다."*
R005 — 근거는 저장소 스크립트가 만든 현물이어야 한다. 그래서 여기로 옮겼다.

게임 파일을 **임시로 바꿨다가 반드시 되돌린다.** 그동안 다른 측정을 돌리면 안 된다.
되돌린 뒤 도장이 시작 때와 같은지 스스로 확인하고 기록에 적는다.

쓰는 법:
    python tools/curve_sweep.py --seeds 8 --cand "ZONE_HP_G=1.62" --cand "ZONE_HP_G=1.63,TIER_COST_MULT=1.4" --out measurements/curve-sweep-YYYY-MM-DD.json
"""
import io, os, re, sys, json, shutil, argparse, hashlib, datetime, statistics, subprocess

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "game", "index.html")
TOOLS = os.path.join(ROOT, "tools")

SNIP = ("import sys, json;"
        "sys.path.insert(0, sys.argv[1]);"
        "import sim_port as S;"
        "rows=[S.auto_run(seed=sd, max_min=900) for sd in range(1, int(sys.argv[2]) + 1)];"
        "print(json.dumps({'tot':[r['total_min'] for r in rows],'z':[r['final_zone'] for r in rows],"
        "'idle':sum(r['idle_buy'] for r in rows),'zm':[r['zone_min'] for r in rows]}))")


def stamp():
    return hashlib.sha256(io.open(GAME, "rb").read()).hexdigest()[:16]


def set_const(txt, name, val):
    new, n = re.subn(r"(\b%s\s*=\s*)-?[\d.]+" % re.escape(name), lambda m: m.group(1) + val, txt, count=1)
    if n != 1:
        raise ValueError("상수 %s 를 게임에서 못 찾았다" % name)
    return new


def score(d, target0=0.6, growth=1.12, tol=0.20):
    """체류 밖 개수 · 빠른/느린 쪽 · 총분 · 최대 이탈. curve_check 와 같은 목표 곡선."""
    stays = {}
    for zm in d["zm"]:
        ks = sorted(int(k) for k in zm)
        for a, b in zip(ks, ks[1:]):
            stays.setdefault(a, []).append(zm[str(b)] - zm[str(a)])
    out, lo, hi, worst = 0, 0, 0, 0.0
    for z in range(1, 30):
        if z not in stays:
            continue
        r = statistics.median(stays[z]) / (target0 * growth ** (z - 1))
        if abs(r - 1) > tol:
            out += 1
            lo += r < 1
            hi += r >= 1
        worst = max(worst, abs(r - 1))
    return dict(체류밖=out, 빠름=lo, 느림=hi, 총분=round(statistics.median(d["tot"]), 1),
                최대이탈=round(worst, 2), 완주=sum(1 for z in d["z"] if z >= 30), 헛돈틱=d["idle"])


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=8)
    ap.add_argument("--cand", action="append", default=[], help='"NAME=val,NAME2=val" — 비우면 지금 값')
    ap.add_argument("--out")
    a = ap.parse_args(argv[1:])
    cands = [("지금 값", {})] + [(c, dict(kv.split("=") for kv in c.split(","))) for c in a.cand]

    s0 = stamp()
    bk = GAME + ".sweep-backup"
    shutil.copy2(GAME, bk)
    rows = []
    try:
        base = io.open(GAME, encoding="utf-8-sig").read()
        print("%-28s | 체류밖 | 빠름 | 느림 |  총분 | 최대이탈 | 완주 | 헛돈" % "후보")
        for name, kv in cands:
            txt = base
            for k, v in kv.items():
                txt = set_const(txt, k.strip(), v.strip())
            io.open(GAME, "w", encoding="utf-8", newline="").write(txt)
            r = subprocess.run([sys.executable, "-c", SNIP, TOOLS, str(a.seeds)],
                               capture_output=True, text=True, encoding="utf-8")
            if r.returncode:
                rows.append({"후보": name, "설정": kv, "실패": (r.stderr or "")[-300:]})
                print("%-28s | 실패" % name)
                continue
            sc = score(json.loads(r.stdout.strip().splitlines()[-1]))
            rows.append(dict({"후보": name, "설정": kv}, **sc))
            print("%-28s | %5d | %4d | %4d | %5.1f | %8.2f | %4d | %4d"
                  % (name, sc["체류밖"], sc["빠름"], sc["느림"], sc["총분"], sc["최대이탈"], sc["완주"], sc["헛돈틱"]))
            sys.stdout.flush()
    finally:
        shutil.move(bk, GAME)
    s1 = stamp()
    print("게임 파일 되돌림: %s" % ("같다" if s0 == s1 else "**다르다 — 손으로 확인하라**"))

    if a.out:
        rec = {"측정일": datetime.date.today().isoformat(), "도구": "tools/curve_sweep.py",
               "시드": list(range(1, a.seeds + 1)),
               "빌드도장": s0, "되돌린_뒤_도장": s1, "되돌림_확인": s0 == s1,
               "목표": "체류(z) = 0.6 x 1.12^(z-1) 분 · 허용 ±20% · curve_check 와 같다",
               "후보별": rows,
               "주의": "후보 행의 숫자는 그 후보를 넣은 임시 게임의 것이다. '지금 값' 행만 이 도장의 게임이다.",
               "판정하지_않는다": "격자는 고르기 위한 것이다. 고른 값의 판정은 curve_check 20시드로 다시 잰다."}
        io.open(a.out, "w", encoding="utf-8").write(json.dumps(rec, ensure_ascii=False, indent=2))
        print("기록: %s" % a.out)
    return 0 if s0 == s1 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
