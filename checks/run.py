# -*- coding: utf-8 -*-
"""검사 러너. 실행: python checks/run.py"""
import io, os, sys, json, glob, datetime, importlib.util, traceback

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

MARK = {"ok": "  OK  ", "fail": " FAIL ", "warn": " WARN ",
        "skip": " SKIP ", "error": "ERROR "}


def load(path):
    name = os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    files = sorted(glob.glob(os.path.join(HERE, "c*.py")))
    results = []
    for f in files:
        base = os.path.basename(f)
        try:
            m = load(f)
            r = m.run(ROOT)
            r.setdefault("detail", [])
            r["check"] = base
            r["name"] = getattr(m, "NAME", base)
            r["priority"] = getattr(m, "PRIORITY", 1)
            results.append(r)
        except Exception:
            results.append({"check": base, "name": base, "priority": 1,
                            "status": "error",
                            "detail": traceback.format_exc().splitlines()[-3:]})

    blocking = [r for r in results
                if r["status"] in ("fail", "error") and r["priority"] == 1]
    warns = [r for r in results
             if r["status"] == "warn" or (r["status"] == "fail" and r["priority"] == 2)]
    skips = [r for r in results if r["status"] == "skip"]

    print("=" * 66)
    for r in results:
        print("[%s] p%d %-22s %s" % (MARK.get(r["status"], "  ??  "),
                                     r["priority"], r["check"], r["name"]))
        for d in r["detail"][:8]:
            print("           - %s" % d)
    print("=" * 66)
    print("차단 %d / 경고 %d / 건너뜀 %d / 전체 %d"
          % (len(blocking), len(warns), len(skips), len(results)))
    if skips:
        print("건너뛴 검사는 통과가 아니다. 이유를 보라 (원칙 2).")

    today = datetime.date.today().isoformat()
    out = os.path.join(ROOT, "measurements", "checks-%s.json" % today)
    with io.open(out, "w", encoding="utf-8") as f:
        json.dump({"ran_at": datetime.datetime.now().isoformat(timespec="seconds"),
                   "blocking": len(blocking), "warn": len(warns),
                   "skip": len(skips), "results": results},
                  f, ensure_ascii=False, indent=2)
    print("기록: %s" % out)
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
