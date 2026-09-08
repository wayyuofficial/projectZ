# 실측 (measurements)

기계가 조회한 원자료만 넣는다. **해석을 섞지 않는다.**

- `env-YYYY-MM-DD.json` — 실행 환경 조회 결과 (`python measurements/probe_env.py`)
- `checks-YYYY-MM-DD.json` — 검사 실행 결과 (`python checks/run.py`)
- `canon-hashes.json` — 정본 파일 해시 (`python tools/approve_canon.py` 로 갱신)

조회에 실패한 항목은 값을 비우지 않고 `"status": "error"` 로 남긴다. 원칙 2.
