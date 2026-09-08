# 게임 (game)

단일 HTML 파일 하나만 둔다. 현재 **비어 있음** (M1 착수 전).

## 검사가 요구하는 약속
```js
const UNIT_TYPES = [ { id: 'knight', ... }, ... ];  // id 개수를 센다. 6 이하
const WAVE_COUNT = 10;   // 10 이하
const STAR_MAX  = 3;     // 3 이하
const SAVE_VERSION = 1;  // localStorage 를 쓰면 필수
```

## 금지
- 외부 `script src` / `link href` / `img src` (data: URI 로 넣는다)
- `fetch` / `XMLHttpRequest` / `WebSocket` / `EventSource` / `sendBeacon`
