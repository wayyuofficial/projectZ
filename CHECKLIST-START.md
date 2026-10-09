# 시작 점검 목록

새 세션을 열 때 이 순서로 확인한다. 3분이면 끝난다.

## 1. 환경이 그대로인가
```bash
python measurements/probe_env.py
```
- `python` 이 `ok` 인가. `node`/`npm` 은 로컬 PC 에선 `error` 가 정상이다. **클라우드 세션에는 node 22 가 있다**(Playwright 로 브라우저 확인·`tools/test_storage.js` 를 돌린다) — 둘을 섞어 비교하지 않는다
- 결과가 이전 `measurements/env-*.json` 과 다르면 **거기서 멈추고 사람에게 보고한다**

## 2. 검사가 통과하는가
```bash
python checks/run.py
```
- 종료 코드 `0` 이어야 한다
- `SKIP` 이 있으면 이유를 읽는다. **건너뛴 검사는 통과가 아니다**

## 3. 검사가 실제로 걸리는가 (검사 코드를 고쳤다면)
```bash
python tools/selftest_checks.py
```
- 8개 전부 위반을 잡아야 한다

## 4. 지금 어디까지 왔나
- `plans/` 의 최신 계획서를 연다 — 예측표에서 **미판정** 항목을 본다
- `instructions-log.md` 맨 뒤 항목 번호를 확인한다

## 5. 무엇을 할지 고른다
- `procedures/00-router.md`

---

## 지금 상태 — 여기 적지 않고 어디서 보는지만 적는다
2026-09-08 의 표("게임 파일 아직 없음 · 소형 오토배틀러")가 M15 까지 그대로 남아 있었다. 날짜 박힌 상태표는 낡는다.

| 알고 싶은 것 | 볼 곳 |
|---|---|
| 게임이 무엇인가 | `canon/00-identity.md` (방치형 좀비 아포칼립스 RPG) |
| 상한(구역·무기·능력치…) | `canon/10-scope.md` 의 기계가 읽는 값 |
| 지금 마일스톤 | `plans/` 에서 가장 큰 `wbs-MN.md` — 진행도 표 |
| 마지막 지시 | `instructions-log.md` 맨 끝 `## 지시 #N` |
| 검사가 지금 통과하나 | `python checks/run.py` (차단 0 이어야 커밋 — R007) |
| 정본 승인 대기인가 | `c0` 이 차단이면 그렇다 — 사람이 `git pull` 뒤 `python tools/approve_canon.py` |
