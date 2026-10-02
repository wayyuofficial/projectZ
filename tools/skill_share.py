# -*- coding: utf-8 -*-
"""M12 3.2 — 스킬 피해가 전체 피해의 몇 퍼센트인지 (예측 M12-P1: 20~35%).

거울(tools/sim_port.py) auto_run 을 끝까지 돌리고 계수기 dmgShot(사격)·dmgSkill(스킬: 수류탄·화염병·관통탄·포탑·지원 사격)을 읽는다.
아드레날린·집중 사격(공격속도)은 사격 피해에 섞인다 — 스킬 몫은 '스킬이 직접 준 피해' 만이다(보수적으로).
쓰는 법: python tools/skill_share.py --seeds 8 [--out measurements/skill-share-....json]"""
import os, sys, json, argparse, statistics, datetime, hashlib, io
from multiprocessing import Pool
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim_port as SP


def one(seed):
    r = SP.auto_run(seed=seed, max_min=900); s = r["sim"]
    tot = s.dmgShot + s.dmgSkill
    return dict(seed=seed, final_zone=r["final_zone"], reach_min=r["zone_min"].get(SP.ZONE_COUNT),
                share=(s.dmgSkill / tot) if tot else 0.0, lv=dict(s.G["skills"]["lv"]), books=s.G.get("books"))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--seeds", type=int, default=8); ap.add_argument("--out")
    a = ap.parse_args()
    with Pool(min(8, os.cpu_count() or 1)) as p:
        rows = p.map(one, range(1, a.seeds + 1))
    for r in rows:
        print("시드 %d: 구역 %d · %s분 · 스킬 몫 %.1f%% · 레벨 %s" % (r["seed"], r["final_zone"], r["reach_min"], r["share"] * 100, r["lv"]))
    med = statistics.median(r["share"] for r in rows)
    print("스킬 몫 중앙 %.1f%% (M12-P1: 20~35%%)" % (med * 100))
    if a.out:
        stamp = hashlib.sha256(io.open(SP.GAME, "rb").read()).hexdigest()[:16]
        json.dump({"측정일": datetime.date.today().isoformat(), "도구": "tools/skill_share.py", "빌드도장": stamp, "시드": a.seeds,
                   "행": rows, "스킬몫_중앙": med}, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("기록:", a.out)
    return 0 if 0.20 <= med <= 0.35 else 1


if __name__ == "__main__":
    sys.exit(main())
