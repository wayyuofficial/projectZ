# -*- coding: utf-8 -*-
"""실행 환경을 조회해 measurements/env-YYYY-MM-DD.json 으로 남긴다.
해석을 넣지 않는다. 조회 실패는 status=error 로 남긴다 (원칙 2)."""
import io, json, os, subprocess, sys, datetime

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROBES = [
    ("python", ["python", "--version"]),
    ("python3_alias", ["python3", "--version"]),
    ("node", ["node", "-v"]),
    ("npm", ["npm", "-v"]),
    ("git", ["git", "--version"]),
]

def probe(cmd):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=20, shell=False)
        out = (p.stdout + p.stderr).strip().splitlines()
        return {"status": "ok" if p.returncode == 0 else "error",
                "returncode": p.returncode,
                "output": out[0] if out else ""}
    except FileNotFoundError:
        return {"status": "error", "returncode": None, "output": "명령 없음 (FileNotFoundError)"}
    except Exception as e:
        return {"status": "error", "returncode": None, "output": "%s: %s" % (type(e).__name__, e)}

def main():
    today = datetime.date.today().isoformat()
    data = {
        "probed_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "root": ROOT,
        "os": {"platform": sys.platform, "name": os.name},
        "commands": {},
    }
    for name, cmd in PROBES:
        data["commands"][name] = probe(cmd)

    out_path = os.path.join(ROOT, "measurements", "env-%s.json" % today)
    with io.open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    errs = [k for k, v in data["commands"].items() if v["status"] == "error"]
    print("실측 기록: %s" % out_path)
    for k, v in data["commands"].items():
        print("  %-14s %-6s %s" % (k, v["status"], v["output"]))
    print("error 항목 %d개: %s" % (len(errs), ", ".join(errs) if errs else "없음"))
    return 0

if __name__ == "__main__":
    sys.exit(main())
