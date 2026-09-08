# 정본 — 스코프 상한 (M1)

근거: instructions-log.md 지시 #5 충돌 처리, 지시 #8·#9 / plans/plan-M1.md 예측 P6 반증 조건
개정: 2026-09-08 — 오토배틀러 어휘(유닛/웨이브/별)에서 방치형 어휘(무기/구역/등급)로 교체. 숫자는 그대로.

이 상한을 넘기면 **M1 실패로 판정한다.** 늘리려면 instructions-log.md에 새 지시 항목으로 남긴 뒤 이 파일을 사람이 고친다.

| 항목 | 상한 | 비고 |
|---|---|---|
| 무기 종류 | 6 | 파이프 / 소총 / 산탄총 / 화염방사기 / 석궁 / 지뢰 |
| 무기 등급 | 3 | **색만 바꾼다** (recolor). 스프라이트를 3배로 그리지 않는다 |
| 구역 | 10 | 5구역마다 보스 |
| 능력치 종류 | 4 | 공격력 / 공격속도 / 최대체력 / 체력회복 |
| 동시 좀비 | 8 | 초과분은 대기열. 성능 상한 |
| 오프라인 보상 | 8시간 | 그 이상은 안 쌓인다 |
| 적 스프라이트 | 좀비 스프라이트 재사용 | 구역별 색 변형 |
| 서버 | 없음 | localStorage만 |

## 기계가 읽는 값 (checks/c2_scope.py 가 참조)
SCOPE_MAX_WEAPON_TYPES = 6
SCOPE_MAX_TIER = 3
SCOPE_MAX_ZONES = 10
SCOPE_MAX_STATS = 4
SCOPE_MAX_ONSCREEN_ZOMBIES = 8

## 게임 HTML이 지켜야 할 약속
```js
const WEAPON_TYPES = [ { id: 'pipe', ... }, ... ];  // id 개수를 센다
const STATS        = [ { id: 'atk',  ... }, ... ];  // id 개수를 센다
const ZONE_COUNT   = 10;
const TIER_MAX     = 3;
const MAX_ONSCREEN_ZOMBIES = 8;
const SAVE_VERSION = 1;
```
