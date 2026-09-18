# -*- coding: utf-8 -*-
"""검사가 실제로 '걸리는지' 확인한다.

통과만 확인한 검사는 검사가 아니다. 일부러 위반 파일을 만들어 넣고
각 검사가 fail/warn 을 내는지 본 뒤, 만든 파일을 지운다.

실행: python tools/selftest_checks.py
"""
import json, io, os, re, sys, glob, time, shutil, importlib.util

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
function draw(){ drawButtons(); drawOffline(); }
</script></body></html>
"""

BAD_RULE = """# R999 - 일부러 망가뜨린 규칙

대상: 자가진단
(근거 줄과 충돌검토 줄이 일부러 빠져 있다)
"""


# ----- 겹쳐 돌리기 금지 -----
# 25차 감사: 이 자가진단은 game/index.html·canon·plans 를 **제자리에서** 고쳤다 되돌린다.
# 다른 측정이나 빌드와 겹쳐 돌면 그쪽이 망가진 파일을 읽는다 (검증자가 APK 도장 DIFF 로 겪었다).
LOCKFILE = os.path.join(ROOT, ".selftest-running")


def _acquire():
    if os.path.exists(LOCKFILE):
        print("자가진단이 이미 돌고 있다 (%s). 겹쳐 돌리면 저장소 파일이 망가진다." % LOCKFILE)
        print("정말 아무도 안 돌고 있으면 그 파일을 지우고 다시 해라.")
        sys.exit(2)
    io.open(LOCKFILE, "w", encoding="utf-8").write("selftest %d\n" % os.getpid())


def _release():
    try:
        os.remove(LOCKFILE)
    except OSError:
        pass


def main():
    _acquire()
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

        # c15: 예측 문구를 몰래 고친 상태를 만든다
        gd = os.path.join(ROOT, "plans", "GAMEDESIGN.md")
        gd_backup = gd + ".selftest-backup"
        if os.path.exists(gd):
            shutil.copy2(gd, gd_backup); made.append(gd_backup)
            _g = io.open(gd, encoding="utf-8").read()
            w(gd, _g.replace("구역 6·8·10 에서 막힌다", "벽이 생긴다 (아무 데서나)"))

        # c13: 밸런스 표의 첫 행을 틀린 값으로 바꿔 fail 이 나야 한다
        csvp = os.path.join(ROOT, "plans", "balance-zones.csv")
        csv_backup = csvp + ".selftest-backup"
        if os.path.exists(csvp):
            shutil.copy2(csvp, csv_backup); made.append(csv_backup)
            _c = io.open(csvp, encoding="utf-8-sig").read().splitlines()
            if len(_c) > 1:
                _c[1] = "1,99999,999,999.9,1,1,1"
            io.open(csvp, "w", encoding="utf-8-sig").write("\n".join(_c) + "\n")

        # c16: **게임 쪽**을 바꾸고 포트를 그대로 두면 fail 이 나야 한다.
        # 9차 감사 지적: 예전 픽스처는 포트의 해시를 망가뜨려 "잠금이 손대졌다"만 증명했고,
        # c16 이 막겠다고 한 것("게임을 고치고 포트를 안 고침")은 증명하지 않았다.
        # 옮긴 함수 본문에 주석 한 조각만 넣는다 — 상수·통신·메타를 보는 다른 검사는 안 건드린다.
        gamep = os.path.join(ROOT, "game", "index.html")
        game_backup = gamep + ".selftest-backup"
        if os.path.exists(gamep):
            shutil.copy2(gamep, game_backup); made.append(game_backup)
            _g2 = io.open(gamep, encoding="utf-8-sig").read()
            _old = "function zoneReward(z) {"
            if _old in _g2:
                _g2 = _g2.replace(_old, _old + " /*selftest*/", 1)
            # c24 (M6 4.2, 2026-09-18): 확률표 0단계 첫 칸을 1 줄여 합 99 로, drawOdds 에 퍼센트 리터럴 한 줄 — 둘 다 fail 이 나야 한다
            if "const TIER_ODDS = [" in _g2 and "function drawOdds() {" in _g2:
                _i = _g2.index("const TIER_ODDS = [") + len("const TIER_ODDS = [")
                _j = _g2.index("]", _i)
                _row = _g2[_i:_j]
                import re as _re
                _first = _re.search(r"-?[\d.]+", _row)
                _g2 = _g2[:_i] + _row[:_first.start()] + ("%.1f" % (float(_first.group(0)) - 1.0)) + _row[_first.end():] + _g2[_j:]
                _g2 = _g2.replace("function drawOdds() {", "function drawOdds() {" + chr(10) + "  ctx.fillText('99.9%', 0, 0);   /*selftest*/", 1)
            io.open(gamep, "w", encoding="utf-8-sig").write(_g2)

        # c2 의 "없어도 되는 선언" 이 실제로 없어도 되는지 (M4 3.2, 2026-09-15).
        # 장비 상한 셋을 **필수**로 만들었다가 c17 이 잡았다 — 옛 본보기에는 그 선언이 없다.
        # 여기서는 게임 파일에서 GEAR_SHAPES 선언을 지워 본다. **c2 는 통과해야 한다.**
        # (지우는 대상은 아래 c16 픽스처가 이미 백업해 둔 game/index.html 이다 — 그 뒤에 돌린다)

        # c17: **기준을 엄하게 만들어** 본보기가 떨어지는지 본다.
        # 이게 c17 이 막겠다고 한 것이다 — "검사가 좋다고 판정된 산출물을 떨어뜨리는가".
        # 정본의 능력치 상한을 5 -> 4 로 되돌리면 c2 가 본보기(능력치 5종)를 떨어뜨린다.
        scope = os.path.join(ROOT, "canon", "10-scope.md")
        scope_backup = scope + ".selftest-backup"
        if os.path.exists(scope):
            shutil.copy2(scope, scope_backup); made.append(scope_backup)
            _sc = io.open(scope, encoding="utf-8").read()
            # M6 (2026-09-18): 정본 값이 5→7 로 바뀌어 글자 치환이 조용히 안 먹었다 — 숫자와 무관하게 4 로 내린다
            w(scope, re.sub(r"SCOPE_MAX_STATS = \d+", "SCOPE_MAX_STATS = 4", _sc))

        # c18: 곡선 밖 기록을 가장 새 것으로 심는다 — 도달 밖 21개, 벽 비 9, 골짜기 0.1 이면 warn 이 나야 한다
        p = os.path.join(ROOT, "measurements", "balance-M3-_selftest.json")
        w(p, '{"벽": true, "곡선밖": [10,11,12,13,14,15,16,17,18,19,20,21], "도달_밖": [10,11], "벽비": {"5": 9.0}, "골짜기": {"5": 0.1}}')
        os.utime(p, (_future, _future)); made.append(p)

        # c19: 판정 근거로 **인용된** 기록의 도장이 옛 빌드면 warn 이 나야 한다.
        # 실제 기록은 안 건드린다 — 인용하는 쪽(wbs)과 인용되는 쪽(기록) 을 둘 다 새로 심는다.
        p = os.path.join(ROOT, "measurements", "balance-M2-_selftest-stale.json")
        w(p, '{"측정일": "2026-09-11", "빌드도장": "0000000000000000"}'); made.append(p)
        p = os.path.join(ROOT, "plans", "wbs-_selftest.md")
        w(p, "# 자가진단용\n\n근거: `balance-M2-_selftest-stale.json`\n"); made.append(p)

        # c18 이 **바탕 기록(새무기 false)** 을 출하 곡선으로 착각하지 않는지.
        # 이 파일이 더 새롭고 숫자는 깨끗하다 — c18 이 이걸 보면 ok 가 되어 위 픽스처의 warn 이 사라진다.
        p = os.path.join(ROOT, "measurements", "balance-M3-_selftest-noweapons.json")
        w(p, '{"벽": true, "새무기": false, "곡선밖": [], "도달_밖": [], "벽비": {"5": 3.0}, "골짜기": {"5": 1.0}}')
        os.utime(p, (_future + 60, _future + 60)); made.append(p)

        # c20: 요청 항목은 있는데 판정 문구 원문이 없는 실기 기록 — fail 이 나야 한다 (R006, 사례 15·20)
        p = os.path.join(ROOT, "measurements", "device-_selftest.json")
        w(p, '{"측정일": "2026-09-14", "요청 절": ["아무거나"]}'); made.append(p)

        # c21: 정본 하한(구역당 3회)보다 적은 매수 기록을 가장 새 것으로 심는다 — warn 이 나야 한다.
        # 2026-09-16 지시 #102 로 판정선이 간격 상한에서 매수 횟수 하한으로 바뀌었다.
        p = os.path.join(ROOT, "measurements", "upgrade-cadence-_selftest.json")
        w(p, '{"구역별": [{"구역": 1, "매수_횟수_중앙": 5, "간격_초_중앙": 30.0}, {"구역": 2, "매수_횟수_중앙": 1, "간격_초_중앙": 12.0}], "매수_3회_미만_구역": [2]}')
        os.utime(p, (_future, _future)); made.append(p)

        # c23: 같은 도장·같은 시드인데 기준선이 다른 기록 둘을 심는다 — warn 이 나야 한다 (2026-09-17, R008)
        for name, field, val in (("sell-share-_selftest.json", "구역30_도달_중앙_분", 100.0),
                                 ("focus-_selftest.json", "안누름_분", 150.0)):
            p = os.path.join(ROOT, "measurements", name)
            w(p, json.dumps({"빌드도장": "selftest00000000", "시드": [1, 2, 3], field: val}, ensure_ascii=False)); made.append(p)

        # c22: **자를 고장 낸다.** 2026-09-16 에 실제로 있던 어긋남을 그대로 되살린다 —
        # 무기 값을 설계도가 아니라 부품과 견주게 한다. 그러면 못 살 무기가 "가장 싼 것" 으로
        # 뽑혀 매수 틱이 멈추고, 살 수 있는 것을 쥔 채 지나간다. fail 이 나야 한다.
        port = os.path.join(ROOT, "tools", "sim_port.py")
        port_backup = port + ".selftest-backup"
        shutil.copy2(port, port_backup); made.append(port_backup)
        _pt = io.open(port, encoding="utf-8").read()
        # M6 (2026-09-18): 무기 상점이 없어져 같은 어긋남을 **뽑기 줄**에 심는다 — 뽑기 횟수를 설계도가 아니라 부품으로 고르면
        # pullGacha(설계도로 결제)가 거부하고, 설계도를 쥔 채 지나간다. fail 이 나야 한다.
        _bug_from = 'n = 10 if s.G.get("plans", 0.0) >= s.gachaCost(10) else (1 if s.G.get("plans", 0.0) >= s.gachaCost(1) else 0)'
        _bug_to   = 'n = 10 if s.G["parts"] >= s.gachaCost(10) else (1 if s.G["parts"] >= s.gachaCost(1) else 0)'
        if _bug_from not in _pt:
            raise SystemExit("자가진단: sim_port 의 뽑기 줄을 못 찾았다 — c22 픽스처를 고쳐라")
        # c25 (사례 26, 2026-09-18): 거울 freshState 에서 게임 저장 칸 하나(boostUntil)를 빼면 fail 이 나야 한다 — 다른 도구는 .get 으로 읽어 안 죽는다
        _pt2 = _pt.replace(_bug_from, _bug_to)
        if "lastSeen=self.now_ms, boostUntil=0)" not in _pt2:
            raise SystemExit("자가진단: sim_port freshState 의 boostUntil 을 못 찾았다 — c25 픽스처를 고쳐라")
        w(port, _pt2.replace("lastSeen=self.now_ms, boostUntil=0)", "lastSeen=self.now_ms)"))

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
            ("c12_draw_order.py", ("warn",)),
            ("c13_balance_table.py", ("fail",)),
            ("c15_prediction_lock.py", ("fail",)),
            ("c16_port_sync.py", ("fail",)),
            ("c17_exemplar_regression.py", ("fail",)),
            ("c18_curve.py", ("warn",)),
            ("c19_evidence_stamp.py", ("warn",)),
            ("c20_request_matches_criterion.py", ("fail",)),
            ("c21_upgrade_cadence.py", ("warn",)),
            ("c22_buyer_not_hoarding.py", ("fail",)),
            ("c23_baseline_agree.py", ("warn",)),
            ("c24_gacha_table.py", ("fail",)),
            ("c25_port_state_keys.py", ("fail",)),
        ]

        bad = []
        print("=" * 60)
        # 도구 자가진단도 여기서 돈다 (22차 감사: curve_check --selftest 가 어디에도 안 걸려 있었다)
        import subprocess
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "curve_check.py"), "--selftest"], capture_output=True, text=True, encoding="utf-8")
        tool_ok = (r.returncode == 0)
        print("[%s] %-22s 기대 %-6s 실제 %s" % ("  OK  " if tool_ok else " MISS ", "curve_check --selftest", "0", r.returncode))
        if not tool_ok:
            bad.append("curve_check --selftest")
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
        gd = os.path.join(ROOT, "plans", "GAMEDESIGN.md")
        gd_backup = gd + ".selftest-backup"
        if os.path.exists(gd_backup):
            shutil.move(gd_backup, gd)
            if gd_backup in made:
                made.remove(gd_backup)
        csvp = os.path.join(ROOT, "plans", "balance-zones.csv")
        csv_backup = csvp + ".selftest-backup"
        if os.path.exists(csv_backup):
            shutil.move(csv_backup, csvp)
            if csv_backup in made:
                made.remove(csv_backup)
        scope = os.path.join(ROOT, "canon", "10-scope.md")
        scope_backup = scope + ".selftest-backup"
        if os.path.exists(scope_backup):
            shutil.move(scope_backup, scope)
            if scope_backup in made:
                made.remove(scope_backup)
        gamep = os.path.join(ROOT, "game", "index.html")
        game_backup = gamep + ".selftest-backup"
        if os.path.exists(game_backup):
            shutil.move(game_backup, gamep)
            if game_backup in made:
                made.remove(game_backup)
        # **남은 백업을 통째로 되돌린다.** 위는 파일마다 한 덩이씩 적혀 있어서,
        # 새로 망가뜨릴 파일을 더할 때 되돌리는 쪽을 빠뜨리기 쉽다. 그러면 자가진단이
        # **저장소를 망가진 채로 두고 끝난다.** 2026-09-16 에 c22 픽스처를 더하면서
        # 실제로 그 자리에 왔다 (sim_port.py). 이 줄이 그 부류를 없앤다.
        for b in glob.glob(os.path.join(ROOT, "**", "*.selftest-backup"), recursive=True):
            shutil.move(b, b[:-len(".selftest-backup")])
            if b in made:
                made.remove(b)
        for p in made:
            if os.path.exists(p):
                os.remove(p)
        left = glob.glob(os.path.join(ROOT, "**", "_selftest*"), recursive=True) + \
            glob.glob(os.path.join(ROOT, "**", "*.selftest-backup"), recursive=True) + \
            glob.glob(os.path.join(ROOT, "rules", "R999-*"))
        if left:
            print("정리 실패로 남은 파일: %s" % left)
        _release()


if __name__ == "__main__":
    sys.exit(main())
