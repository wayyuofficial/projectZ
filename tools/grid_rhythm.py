# -*- coding: utf-8 -*-
"""M15 1.1 — 리듬 격자. 게임 파일은 안 건드리고 거울 상수를 자식 프로세스 안에서만 바꿔(overrides) 잰다.
   잰다: 구역 60 도달 · 사망 · 벽 비(중앙·최대) · 골짜기 최소 · 구역 2~20 도달/목표 누적(최소·최대) — M15-P1·P2 의 숫자.
   쓰는 법: python tools/grid_rhythm.py --seeds 4 --name A "" "WALL_HP_MULT=2" "HP_POW=0.5;ZONE_HP0=30"
   기록: measurements/grid-rhythm-<이름>-<날짜>.json"""
import sys, os, io, json, argparse, statistics, hashlib, datetime
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools")); sys.path.insert(0, ROOT)
import sim_port as SP
import curve_check as CC


def parse(spec):
    o = {}
    for kv in spec.split(";"):
        if kv.strip():
            k, v = kv.split("=", 1); v = v.strip(); o[k.strip()] = json.loads(v) if v.startswith("[") else float(v)   # 표는 JSON
    return o


def run(spec, seeds, max_min):
    rows = SP.run_many(seeds, kw={"max_min": max_min}, overrides=parse(spec) or None)
    stay = {}
    for z in range(1, SP.ZONE_COUNT):
        d = [r["zone_min"][z + 1] - r["zone_min"][z] for r in rows if z + 1 in r["zone_min"]]
        if d: stay[z] = statistics.median(d)
    reach = {z: statistics.median([r["zone_min"][z] for r in rows if z in r["zone_min"]])
             for z in range(1, SP.ZONE_COUNT + 1) if all(z in r["zone_min"] for r in rows)}
    walls = {z: stay[z] / ((stay[z - 1] + stay[z + 1]) / 2) for z in range(SP.WALL_START, SP.ZONE_COUNT, SP.WALL_EVERY) if all(k in stay for k in (z - 1, z, z + 1))}
    trough = {z: stay[z + 1] / stay[z - 1] for z in walls if stay[z - 1] > 0}
    arr = {z: reach[z] / CC.target_arrive(z) for z in range(2, 21) if z in reach and CC.target_arrive(z) > 0}
    wv = sorted(walls.values())
    return {"60도달": round(reach.get(SP.ZONE_COUNT, float("nan")), 1), "완주": sum(1 for r in rows if SP.ZONE_COUNT in r["zone_min"]),
            "사망": statistics.median([r["deaths"] for r in rows]),
            "벽비_중앙": round(statistics.median(wv), 2) if wv else None, "벽비_최대": round(wv[-1], 2) if wv else None,
            "골짜기_최소": round(min(trough.values()), 2) if trough else None,
            "도달비_2_20_최소": round(min(arr.values()), 2) if arr else None, "도달비_2_20_최대": round(max(arr.values()), 2) if arr else None,
            "도달비": {z: round(v, 2) for z, v in arr.items() if z in (2, 3, 5, 10, 15, 20)},
            "도달밖_20": sorted(z for z in reach if CC.target_arrive(z) > 0 and abs(reach[z] / CC.target_arrive(z) - 1) > 0.2 + 1e-9),   # c18 새 선(±20%, 4개 미만)
            "벽비": {z: round(v, 2) for z, v in walls.items()}, "골짜기": {z: round(v, 2) for z, v in trough.items()},
            "도달비_30_60": {z: round(reach[z] / CC.target_arrive(z), 2) for z in (30, 40, 50, 60) if z in reach}}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=4)
    ap.add_argument("--max-min", type=int, default=600)
    ap.add_argument("--name", default="x")
    ap.add_argument("specs", nargs="*")
    a = ap.parse_args()
    seeds = list(range(1, a.seeds + 1)); out = {}
    for s in (a.specs or [""]):
        out[s or "지금 값"] = run(s, seeds, a.max_min); print(s or "지금 값", json.dumps(out[s or "지금 값"], ensure_ascii=False), flush=True)
    stamp = hashlib.sha256(io.open(os.path.join(ROOT, "game", "index.html"), "rb").read()).hexdigest()[:16]
    rec = {"측정일": datetime.date.today().isoformat(), "대상": "M15 1.1 리듬 격자(%s) — 게임 상수는 안 바꿈, 거울 overrides" % a.name,
           "빌드도장": stamp, "시드": seeds, "max_min": a.max_min, "결과": out, "판정하지_않는다": "M15-P1·P2 판정은 사람"}
    io.open(os.path.join(ROOT, "measurements", "grid-rhythm-%s-%s.json" % (a.name, datetime.date.today().isoformat())), "w", encoding="utf-8", newline="").write(json.dumps(rec, ensure_ascii=False, indent=1))
