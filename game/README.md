# 게임 (game)

단일 HTML 파일 하나만 둔다: `index.html` — 방치형 좀비 아포칼립스 RPG (`canon/00-identity.md`).
그림(주인공·좀비·보스·배경·아이콘)은 전부 WebP data URI 로 파일 안에 들어 있다. 파일 크기 상한은 `checks/c27` 이 본다.

## 여는 법
- PC: `index.html` 을 브라우저로 연다. 세로 화면(폰 비율)에 맞춰 그린다.
- 폰: `android/` 래퍼가 이 폴더를 그대로 assets 로 쓴다(복사본을 두지 않는다) — `android/README.md`.

## 숫자는 여기 적지 않는다
상한(구역·무기·능력치·등급 등)은 `canon/10-scope.md` 의 **기계가 읽는 값**이 정한다.
이 파일에 숫자를 적으면 낡는다(이 README 도 M1 시절 "비어 있음 · 무기 6 · 구역 10" 으로 M15 까지 남아 있었다).

## 검사가 요구하는 약속 (checks/c2_scope.py · c5_save_version.py · c16 · c25)
```js
const WEAPON_TYPES = [ { id: ..., ... }, ... ];  // id 개수 <= 정본 SCOPE_MAX_WEAPON_TYPES
const STATS        = [ { id: ..., ... }, ... ];  // id 개수 <= 정본 SCOPE_MAX_STATS
const ZONE_COUNT   = ...;                        // <= 정본 SCOPE_MAX_ZONES
const TIER_MAX     = ...;                        // <= 정본 SCOPE_MAX_TIER
const MAX_ONSCREEN_ZOMBIES = ...;                // <= 정본 SCOPE_MAX_ONSCREEN_ZOMBIES
const SAVE_VERSION = ...;  // 저장 구조가 바뀌면 올리고, migrate() 가 옛 버전을 끌어올린다 — 초기화하지 않는다
```
- 전투·저장 함수는 `tools/sim_port.py`(거울)와 해시로 잠겨 있다. 고치면 거울도 같이 고치고 `python tools/sim_port.py --reseal` (c16).
- 저장 칸(freshState)은 거울과 같은 칸을 가져야 한다 (c25).

## 금지 (checks/c3_no_network.py · c6_single_file.py)
- 외부 `script src` / `link href` / `img src` (data: URI 로 넣는다)
- `fetch` / `XMLHttpRequest` / `WebSocket` / `EventSource` / `sendBeacon`
