# 정본 — 스코프 상한 (M1)

근거: instructions-log.md 지시 #5 충돌 처리 / plans 예측 P6 반증 조건

이 상한을 넘기면 **M1 실패로 판정한다.** 늘리려면 instructions-log.md에 새 지시 항목으로 남긴 뒤 이 파일을 사람이 고친다.

| 항목 | 상한 |
|---|---|
| 유닛 종류 | 6 |
| 별 등급 | 3 (색만 바꿈 — recolor 활용) |
| 웨이브 | 10 |
| 적 스프라이트 | 유닛 스프라이트 재사용 |
| 서버 | 없음. localStorage만 |

## 기계가 읽는 값 (checks/c2_scope.py 가 참조)
SCOPE_MAX_UNIT_TYPES = 6
SCOPE_MAX_WAVES = 10
SCOPE_MAX_STAR = 3
