# -*- coding: utf-8 -*-
"""git 훅을 켠다 — 차단이 있으면 커밋이 거절된다 (R007).

    python tools/install_hooks.py

`.githooks/` 는 저장소에 들어 있다. 이 스크립트는 git 에게 그 폴더를 보라고 알려줄 뿐이다
(`git config core.hooksPath .githooks`). 저장소를 새로 받은 사람도 이 한 줄이면 같은 보호를 받는다.
"""
import os, sys, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    hook = os.path.join(ROOT, ".githooks", "pre-commit")
    if not os.path.exists(hook):
        print("`.githooks/pre-commit` 이 없다. 저장소가 온전한지 본다.")
        return 1
    r = subprocess.run(["git", "config", "core.hooksPath", ".githooks"], cwd=ROOT)
    if r.returncode != 0:
        print("git config 에 실패했다.")
        return 1
    try:
        os.chmod(hook, 0o755)
    except OSError:
        pass
    print("켰다: core.hooksPath = .githooks")
    print("이제 `checks/run.py` 가 차단을 내면 git 이 커밋을 거절한다 (R007).")
    print("넘기려면 git commit --no-verify — 쓴 이유를 instructions-log.md 에 적는다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
