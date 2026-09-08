# 게임 (game)

단일 HTML 파일 하나만 둔다. 현재 **비어 있음** (M1 착수 전).

장르: 방치형 좀비 아포칼립스 RPG — `canon/00-identity.md` 참조.

## 검사가 요구하는 약속 (checks/c2_scope.py · c5_save_version.py)
```js
const WEAPON_TYPES = [ { id: 'pipe', ... }, ... ];  // id 개수 <= 6
const STATS        = [ { id: 'atk',  ... }, ... ];  // id 개수 <= 4
const ZONE_COUNT   = 10;   // <= 10
const TIER_MAX     = 3;    // <= 3
const MAX_ONSCREEN_ZOMBIES = 8;  // <= 8
const SAVE_VERSION = 1;    // localStorage 를 쓰면 필수
```

## 금지 (checks/c3_no_network.py · c6_single_file.py)
- 외부 `script src` / `link href` / `img src` (data: URI 로 넣는다)
- `fetch` / `XMLHttpRequest` / `WebSocket` / `EventSource` / `sendBeacon`
