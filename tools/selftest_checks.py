# -*- coding: utf-8 -*-
"""검사가 실제로 '걸리는지' 확인한다.

통과만 확인한 검사는 검사가 아니다. 일부러 위반 파일을 만들어 넣고
각 검사가 fail/warn 을 내는지 본 뒤, 만든 파일을 지운다.

실행: python tools/selftest_checks.py
"""
import io, os, sys, glob, time, shutil, importlib.util

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKS = os.path.join(ROOT, "checks")
BAD_CMD = "py" + "thon3"          # C7 이 자기 자신을 잡지 않도록 쪼갠다


def load(name):
    p = os.path.join(CHECKS, name)
    spec = importlib.util.spec_from_file_location(name[:-3], p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def w(path, text):
    with io.open(path, "w", encoding="utf-8") as f:
        f.write(text)


BAD_GAME = """<!doctype html><html><body>
<script src="engine.js"></script>
<script>
const WEAPON_TYPES = [
  {id:'a'},{id:'b'},{id:'c'},{id:'d'},{id:'e'},{id:'f'},{id:'g'},{id:'h'}
];
const STATS = [
  {id:'atk'},{id:'spd'},{id:'hp'},{id:'reg'},{id:'crit'},{id:'luck'}
];
const ZONE_COUNT = 20;
const TIER_MAX = 9;
const MAX_ONSCREEN_ZOMBIES = 99;
localStorage.setItem('save', '{}');
fetch('https://example.com/score');
</script></body></html>
"""

BAD_RULE = """# R999 - 일부러 망가뜨린 규칙

대상: 자가진단
(근거 줄과 충돌검토 줄이 일부러 빠져 있다)
"""


def main():
    made = []
    try:
        p = os.path.join(ROOT, "game", "_selftest.html"); w(p, BAD_GAME); made.append(p)
        # c9 는 파일 시각을 본다. 측정 기록과 1초 이내면 판정이 흔들리므로
        # 픽스처 시각을 확실히 미래로 못 박는다 (흔들리는 검사는 검사가 아니다)
        _future = time.time() + 3600
        os.utime(p, (_future, _future))
        p = os.path.join(ROOT, "rules", "R999-자가진단.md"); w(p, BAD_RULE); made.append(p)
        p = os.path.join(ROOT, "procedures", "_selftest.md")
        w(p, "이 줄은 일부러 잘못된 명령을 쓴다: " + BAD_CMD + " checks/run.py\n"); made.append(p)

        # c4(예측·반증 없는 계획서) + c8(원본과 어긋난 뷰) 겸용 픽스처
        p = os.path.join(ROOT, "plans", "_selftest.md")
        w(p, "# 일부러 예측 없는 계획\n\n할 일: 아무거나\n"); made.append(p)
        p = os.path.join(ROOT, "plans", "_selftest.html")
        w(p, "<!-- source-sha256: " + "0" * 64 + " -->\n<p>일부러 어긋난 뷰</p>\n"); made.append(p)

        # c11: WebView 의 DOM Storage 를 주석 처리해 fail 이 나야 한다
        act = os.path.join(ROOT, "android", "app", "src", "main", "java",
                           "com", "wayyu", "zombiesurvival", "MainActivity.java")
        act_backup = act + ".selftest-backup"
        if os.path.exists(act):
            shutil.copy2(act, act_backup); made.append(act_backup)
            _src = io.open(act, encoding="utf-8").read()
            w(act, _src.replace("s.setDomStorageEnabled(true);", "// s.setDomStorageEnabled(true);"))

        canon = os.path.join(ROOT, "canon", "00-identity.md")
        backup = canon + ".selftest-backup"
        shutil.copy2(canon, backup); made.append(backup)
        with io.open(canon, "a", encoding="utf-8") as f:
            f.write("\n<!-- selftest -->\n")

        expect = [
            ("c0_canon_lock.py", ("fail",)),
            ("c1_rule_hygiene.py", ("fail",)),
            ("c2_scope.py", ("fail",)),
            ("c3_no_network.py", ("fail",)),
            ("c5_save_version.py", ("warn",)),
            ("c6_single_file.py", ("warn",)),
            ("c4_plan_hygiene.py", ("fail",)),
            ("c7_python_cmd.py", ("fail",)),
            ("c8_view_freshness.py", ("warn",)),
            ("c9_measurement_freshness.py", ("warn",)),
            ("c10_html_meta.py", ("fail",)),
            ("c11_webview_storage.py", ("fail",)),
        ]

        bad = []
        print("=" * 60)
        for name, want in expect:
            got = load(name).run(ROOT).get("status")
            ok = got in want
            print("[%s] %-22s 기대 %-6s 실제 %s" %
                  ("  OK  " if ok else " MISS ", name, "/".join(want), got))
            if not ok:
                bad.append("%s : 기대 %s, 실제 %s" % (name, want, got))
        print("=" * 60)

        if bad:
            print("자가진단 실패 %d건 — 이 검사들은 위반을 못 잡는다:" % len(bad))
            for b in bad:
                print("  - %s" % b)
            return 1
        print("자가진단 통과: 검사 %d개 전부 위반을 잡아낸다." % len(expect))
        return 0

    finally:
        canon = os.path.join(ROOT, "canon", "00-identity.md")
        backup = canon + ".selftest-backup"
        if os.path.exists(backup):
            shutil.move(backup, canon)
            if backup in made:
                made.remove(backup)
        act = os.path.join(ROOT, "android", "app", "src", "main", "java",
                           "com", "wayyu", "zombiesurvival", "MainActivity.java")
        act_backup = act + ".selftest-backup"
        if os.path.exists(act_backup):
            shutil.move(act_backup, act)
            if act_backup in made:
                made.remove(act_backup)
        for p in made:
            if os.path.exists(p):
                os.remove(p)
        left = glob.glob(os.path.join(ROOT, "**", "_selftest*"), recursive=True) + \
            glob.glob(os.path.join(ROOT, "rules", "R999-*"))
        if left:
            print("정리 실패로 남은 파일: %s" % left)


if __name__ == "__main__":
    sys.exit(main())
