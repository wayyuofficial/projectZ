# -*- coding: utf-8 -*-
"""`game/index.html` 의 게임 로직을 파이썬으로 옮긴 것. **저장소의 자산이다.**

## 왜 있는가

이 환경에는 브라우저도 node 도 없다. 그래서 게임을 판정하려면 로직을 옮겨서 돌려야 한다.
그런데 감사 회차마다 검증자가 포트를 새로 짜고 있었다. 그 결과:

- 회차당 17분이 걸렸다 (2026-09-09 8차 감사 실측: 17.0분 / 도구 53회 / 토큰 147k)
- **포트가 회차마다 달라졌다.** 8차 시점에 두 포트가 구역5 도달 시간에서 25% 어긋났다
  (만든 쪽 9.5분 vs 검증자 7.6분, 범위가 겹치지도 않았다).
  같은 게임을 두고 두 숫자가 나오면 둘 다 못 쓴다.

그래서 포트를 하나로 만들어 저장소에 넣고, **게임이 바뀌면 검사가 잡게 했다.**

## 이 파일이 지키는 규칙

1. **상수를 여기에 적지 않는다.** 전부 `game/index.html` 에서 뽑아 쓴다 (아래 `num()`).
   숫자를 베껴 적으면 게임이 바뀌었을 때 조용히 어긋난다.
2. **옮긴 함수 목록(`MIRRORED`)을 원본 본문 해시와 함께 들고 있다.**
   원본이 바뀌면 `checks/c16_port_sync.py` 가 막는다. 그때 **사람이 포트를 다시 맞추고**
   `python tools/sim_port.py --reseal` 로 해시를 다시 찍는다.
3. **난수는 게임과 같을 수 없다.** 게임은 `Math.random()` 을 쓴다.
   여기 시드는 *이 포트를 결정적으로 만들기 위한 것*이지 게임과 같은 수열이 아니다.
   그러므로 **시드 하나의 값을 게임의 값이라고 말하면 안 된다.** 여러 시드의 분포로만 말한다.

## 옮긴 것 / 안 옮긴 것

옮긴 것: 상태 · 전투 · 저장(`migrate`) · 오프라인 · 구매 · **배치(`layout`/`fit_game`)** ·
**버튼 자리(`buildButtons`)**. 배치와 버튼은 9차 감사 지적으로 추가했다 —
이게 없으면 1.1·7.1·7.2 를 회차마다 다시 옮겨야 해서 빠른 회차가 안 빨라진다.

안 옮긴 것: 그리기(`draw*`) · 입력 · 캔버스 · `localStorage` · 버튼의 **글자**.
이 포트로 "화면이 이렇게 보인다"를 판정하지 않는다. 그건 사람이나 실기가 한다.
버튼은 **자리와 상태**만 있고 label/sub 는 없다 — 글자 판정에 쓰지 마라.

실행: `python tools/sim_port.py`          — 자기 점검 (상수 대조 + 짧은 런)
      `python tools/sim_port.py --reseal` — 원본을 다시 읽어 해시를 찍는다 (사람이 확인한 뒤에만)
"""
import io, os, re, sys, math, json, hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "game", "index.html")

with io.open(GAME, encoding="utf-8-sig", errors="replace") as _f:
    SRC = _f.read()


# ── 원본에서 뽑아 쓴다 ────────────────────────────────────────────────
def num(name):
    """`const NAME = 1.23` 또는 `NAME = 1.23,` 형태에서 숫자를 뽑는다."""
    m = re.search(r"const\s+" + name + r"\s*=\s*(-?[\d.]+)", SRC) \
        or re.search(r"\b" + name + r"\s*=\s*(-?[\d.]+)\s*[,;]", SRC)
    if not m:
        raise ValueError("game/index.html 에서 상수 %s 를 못 찾았다" % name)
    return float(m.group(1))


def table(name):
    """`const NAME = [ {...}, ... ];` 를 파이썬 dict 목록으로 바꾼다."""
    m = re.search(r"const\s+" + name + r"\s*=\s*\[(.*?)\n\];", SRC, re.S)
    if not m:
        raise ValueError("game/index.html 에서 표 %s 를 못 찾았다" % name)
    out = []
    for row in re.finditer(r"\{([^{}]*)\}", m.group(1)):
        d = {}
        for k, v in re.findall(r"(\w+)\s*:\s*('[^']*'|\"[^\"]*\"|-?[\d.]+|true|false)", row.group(1)):
            d[k] = v[1:-1] if v[0] in "'\"" else (v == "true" if v in ("true", "false") else float(v))
        out.append(d)
    return out


SAVE_VERSION = int(num("SAVE_VERSION"))
ZONE_COUNT = int(num("ZONE_COUNT"))
TIER_MAX = int(num("TIER_MAX"))
MAX_ONSCREEN_ZOMBIES = int(num("MAX_ONSCREEN_ZOMBIES"))
ZONE_HP0, ZONE_HP_G = num("ZONE_HP0"), num("ZONE_HP_G")
ZONE_RW0, ZONE_RW_G = num("ZONE_RW0"), num("ZONE_RW_G")
WALL_EVERY, WALL_KILL_MULT, WALL_START = int(num("WALL_EVERY")), int(num("WALL_KILL_MULT")), int(num("WALL_START"))   # M2 벽 (처치 수, 구역 10 부터)
ZOMBIE_DPS_RATIO = num("ZOMBIE_DPS_RATIO")
STAGES_PER_ZONE = int(num("STAGES_PER_ZONE"))
STAGE_BONUS_RATIO = num("STAGE_BONUS_RATIO")
FOCUS_MULT = num("FOCUS_MULT")
TIER_MAX_PORT = int(num("TIER_MAX"))
GEAR_SHAPES = int(num("GEAR_SHAPES"))
GEAR_AFFIXES = int(num("GEAR_AFFIXES"))
BAG_MAX = int(num("BAG_MAX"))
AUTOSELL_ZONE = int(num("AUTOSELL_ZONE"))
GEAR_SLOT_IDS = ["weapon", "head", "body", "hands", "feet"]
AFFIX_IDS = ["hp", "reg", "atk", "spd", "inc"]
AFFIX_PER = {"hp": 0.18, "reg": 0.15, "atk": 0.10, "spd": 0.08, "inc": 0.09}
KEY_MAX = int(num("KEY_MAX"))
SUPPLY_SHARE = num("SUPPLY_SHARE")
LOGIN_DAYS = int(num("LOGIN_DAYS"))
DAY_MS = int(num("DAY_MS"))
LOGIN_SHARES = [float(x) for x in re.search(
    r"const\s+LOGIN_SHARES\s*=\s*\[([^\]]*)\]", SRC).group(1).replace(" ", "").split(",") if x]
DAILY_BUDGET = num("DAILY_BUDGET")
BP_RATIO = num("BP_RATIO")
BP_STAGE_SHARE = num("BP_STAGE_SHARE")
BP_BOSS_SHARE = num("BP_BOSS_SHARE")
BP_OFFLINE_SHARE = num("BP_OFFLINE_SHARE")
KILLS_PER_ZONE = int(num("KILLS_PER_ZONE"))
BOSS_EVERY = int(num("BOSS_EVERY"))
BOSS_HP_MULT = num("BOSS_HP_MULT")
BOSS_CHARGE_EVERY = num("BOSS_CHARGE_EVERY")
BOSS_CHARGE_TIME = num("BOSS_CHARGE_TIME")
BOSS_CHARGE_MULT = num("BOSS_CHARGE_MULT")
TIER_COST_MULT = num("TIER_COST_MULT")
TIER_POWER = num("TIER_POWER")
OFFLINE_MAX_HOURS = num("OFFLINE_MAX_HOURS")
OFFLINE_RATE = num("OFFLINE_RATE")
AD_BOOST_MIN = num("AD_BOOST_MIN")
GAME_W = num("GAME_W")
MIN_GAME_H = num("MIN_GAME_H")
MAX_GAME_H = num("MAX_GAME_H")
MAX_BACK_W = num("MAX_BACK_W")
HUD_H = num("HUD_H")
PANEL_H_MIN = num("PANEL_H_MIN")
PANEL_H_MAX = num("PANEL_H_MAX")
PANEL_H_RATIO = num("PANEL_H_RATIO")
ARENA_MIN = num("ARENA_MIN")
ARENA_TOP = HUD_H                    # 원본도 ARENA_TOP = HUD_H 다
SURVIVOR_X = num("SURVIVOR_X")
CONTACT_X = SURVIVOR_X + 46          # 원본도 SURVIVOR_X + 46 으로 쓴다
ZOMBIE_GAP = num("ZOMBIE_GAP")
CONTACT_REACH = num("CONTACT_REACH")
SPAWN_X = GAME_W + 36
FIXED_STEP = 1.0 / 60
DEFAULT_NOW_MS = 1000000000000   # 포트 시계의 시작(UTC 2001-09-09 01:46). 시간대 과제(M4 1.2)를 잴 때는 auto_run(now_ms=) 로 옮긴다
MAX_STEPS = int(num("MAX_STEPS"))
MAX_GAP = num("MAX_GAP")
REVIVE_OFFER_SEC = num("REVIVE_OFFER_SEC")
ROW_H = num("ROW_H")
ROW_GAP = num("ROW_GAP")
ROW_PITCH = ROW_H + ROW_GAP
MIN_TAP_CSS = num("MIN_TAP_CSS")

STATS = table("STATS")
WEAPON_TYPES = table("WEAPON_TYPES")
# M4 4.3 (a) 2026-09-17 — 장비로만 오르는 축. **원본의 gearOnly 에서 읽는다.** 여기 손으로 적으면
# 원본과 갈라진다 (사례 23: 한 개념이 두 곳에 있으면 한 곳은 남는다).
GEAR_ONLY_STATS = {s["id"] for s in STATS if s.get("gearOnly")}
# M4 1.2 (a) 2026-09-17 — 과제도 원본 표에서 읽는다. 전에는 need 를 손으로 베껴 두고 "바뀌면 여기도" 라고 적었다.
QUEST_DEFS = table("QUEST_DEFS")
QUEST_DEFS_IDS = [q["id"] for q in QUEST_DEFS]
QUEST_NEEDS = {q["id"]: int(q["need"]) for q in QUEST_DEFS}
QUEST_SHARES = {q["id"]: float(q["share"]) for q in QUEST_DEFS}
QUEST_BANDS = [int(x) for x in re.search(r"const\s+QUEST_BANDS\s*=\s*\[([^\]]*)\]", SRC).group(1).replace(" ", "").split(",") if x]


# ── 원본 함수 본문을 그대로 떠서 해시한다 ─────────────────────────────
def js_function(name):
    """`function name(` 부터 짝이 맞는 `}` 까지의 원문을 돌려준다."""
    m = re.search(r"^function\s+" + name + r"\s*\(", SRC, re.M)
    if not m:
        raise ValueError("game/index.html 에서 함수 %s 를 못 찾았다" % name)
    i = SRC.index("{", m.end() - 1)
    depth, j = 0, i
    while j < len(SRC):
        c = SRC[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return SRC[m.start():j + 1]
        j += 1
    raise ValueError("함수 %s 의 끝을 못 찾았다" % name)


def fingerprint(name):
    """공백만 정규화해서 해시한다. 들여쓰기 변경으로는 안 걸리고 코드 변경으로는 걸린다."""
    body = re.sub(r"\s+", " ", js_function(name)).strip()
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]


# 여기 적힌 함수는 아래 파이썬 구현이 **거울**이다.
# 원본이 바뀌면 c16 이 막는다. 막히면 아래 구현을 손으로 다시 맞춘 뒤 --reseal 한다.
MIRRORED = {
    "acceptRevive": "76080cff2a1316f8",
    "adRowY": "5ed5d78e1b23b919",
    "applyDamage": "44f3fc0acd0ea484",
    "applyOffline": "22e6b2208ac61edc",
    "attacksPerSec": "62c1a324deffd5c2",
    "boostActive": "ed9a9a513325e7ef",
    "buildButtons": "8d2a997905d62c0e",
    "buyStat": "55e7f37e19e75aee",
    "buyWeapon": "e58bfe7e010aeddb",
    "dailyBudget": "51f1b98162132ed0",
    "damageZombie": "9dfa910d5cf6855b",
    "dayIndex": "e395fb011be7dfbc",
    "dropGear": "990bf216887801f8",
    "equip": "c815c6819c3b6edb",
    "fitGame": "d526a00619b69c86",
    "freshState": "15bc5afe1f90d9aa",
    "gearMult": "c2392bb827fd20df",
    "gearScore": "d7dd0e82bc73c578",
    "gearSellPrice": "81a178c6a44a414e",
    "hitButton": "8564f49dbd9cc319",
    "hitDamage": "78764110ba1a3fdd",
    "isBossKill": "e461a4a51bbb69c5",
    "killReward": "0ef3ffe5d2eb73ba",
    "killZombie": "75529bacc76c2f24",
    "layout": "a6a07a236eb89472",
    "listBotY": "58cb9bb82a45c13d",
    "listTopY": "46bb14aa20673823",
    "maxHP": "85e54826f897f7c7",
    "migrate": "edff5237d7500f64",
    "onDeath": "589239f3a352fe82",
    "openSupply": "39e13a85803de479",
    "partsPerSecondEstimate": "424babe8c5fc62f9",
    "playerDPS": "6e388f9e36329ce1",
    "questBand": "47a268e16a55bfbd",
    "questOpen": "14e21773cabeb67b",
    "questReady": "d56a30909b205279",
    "regenPerSec": "73badd17c9fc2857",
    "rewardMult": "bff5bcb3e94a3395",
    "rollGear": "c082d7808bc48c0e",
    "rollTier": "802162caae06b933",
    "rolloverDay": "6fc592cf03b69d34",
    "spawnZombie": "d4054c63f48a4d4a",
    "stageKills": "4cb2b09008d21635",
    "statCost": "3915c9b212b37571",
    "statDef": "e7ad6087978fd6ec",
    "statOf": "ce944d01f686e148",
    "stepCombat": "477e00f37b335b3e",
    "tabRowY": "d001ac81a8afa161",
    "takeQuest": "a0118e0f6668c7ca",
    "weaponOf": "cd23351858d3c448",
    "weaponPower": "0a8ae8face6a1394",
    "weaponUpgradeCost": "57e23cd55b81ff51",
    "zoneDPS": "9abab3ae0b004352",
    "zoneHP": "eafea50cbb2f5af6",
    "zoneReward": "1a11949b7141abd1",
}


def drift():
    """원본이 바뀐 함수 목록. 비어 있으면 포트가 원본과 맞물려 있다는 뜻이다."""
    out = []
    for name, want in sorted(MIRRORED.items()):
        try:
            got = fingerprint(name)
        except ValueError as e:
            out.append((name, want, "없음(%s)" % e))
            continue
        if got != want:
            out.append((name, want, got))
    return out


# ── 배치 — 원본에서 전역인 것들. 여기서도 모듈 전역으로 둔다 ─────────
L = {"GAME_H": 960.0, "PANEL_H": 420.0, "PANEL_TOP": 540.0, "ARENA_BOT": 530.0, "GROUND_Y": 478.0,
     "cssW": 0.0, "cssH": 0.0, "backW": 0.0, "backH": 0.0, "dpr": 1.0}


def jsround(x):
    """JS 의 Math.round 는 floor(x+0.5) 다. 파이썬 round() 는 짝수로 붙이는 은행가 반올림이라
    .5 에서 갈린다 — iPhone SE 320x568 의 GAME_H 가 브라우저 959 vs 포트 958 로 실제로 어긋났다
    (2026-09-09 12차 감사 적발. 격자로 세면 5.03% 조합에서 1px 차이)."""
    return math.floor(x + 0.5)


def layout(zombies=None):
    """원본 `layout()`. 바닥선이 움직이면 살아 있는 좀비도 같이 옮긴다."""
    prev = L["GROUND_Y"]
    L["PANEL_H"] = max(PANEL_H_MIN,
                   min(PANEL_H_MAX,
                   min(jsround(L["GAME_H"] * PANEL_H_RATIO), L["GAME_H"] - ARENA_TOP - ARENA_MIN - 10)))
    L["PANEL_TOP"] = L["GAME_H"] - L["PANEL_H"]
    L["ARENA_BOT"] = L["PANEL_TOP"] - 10
    L["GROUND_Y"] = L["ARENA_BOT"] - 52
    dy = L["GROUND_Y"] - prev
    if dy and zombies:
        for z in zombies:
            z["y"] += dy


def fit_game(vw, vh, device_dpr=1.0, zombies=None):
    """원본 `fitGame()`. 캔버스가 없으므로 크기 계산만 한다.

    돌려주는 것: 논리 세로 · CSS 크기 · 백버퍼 크기 · 실제 dpr · 여백 비율."""
    L["GAME_H"] = max(MIN_GAME_H, min(MAX_GAME_H, jsround(GAME_W * vh / max(1, vw))))
    asp = GAME_W / L["GAME_H"]
    layout(zombies)
    if vw / float(vh) > asp:
        h, w = float(vh), vh * asp
    else:
        w, h = float(vw), vw / asp
    L["cssW"], L["cssH"] = jsround(w), jsround(h)
    L["dpr"] = device_dpr                      # 원본이 DPR 상한 3 을 없앴다 (10차 감사)
    L["backW"] = jsround(L["cssW"] * L["dpr"])
    if L["backW"] > MAX_BACK_W:
        L["backW"] = MAX_BACK_W
        L["dpr"] = L["backW"] / float(L["cssW"])
    L["backH"] = jsround(L["cssH"] * L["dpr"])
    waste = 1.0 - (L["cssW"] * L["cssH"]) / float(vw * vh)
    # 판정 ② 는 "백버퍼 = CSS 크기 x DPR" 이다. 여기서 DPR 은 **기기의** DPR 이지
    # 코드가 잘라 쓴 값이 아니다. 잘린 값으로 재면 backW = round(cssW*dpr) 라
    # **구조상 실패가 불가능한 항등식**이 된다 (10차 감사가 이 구멍을 뚫었다).
    # 그래서 기기 DPR 기준 오차를 따로 돌려준다.
    return dict(GAME_H=L["GAME_H"], cssW=L["cssW"], cssH=L["cssH"],
                backW=L["backW"], backH=L["backH"],
                dpr=L["dpr"], device_dpr=device_dpr,
                err_w=abs(L["backW"] - L["cssW"] * device_dpr),
                err_h=abs(L["backH"] - L["cssH"] * device_dpr),
                max_back_w_clamped=L["backW"] >= MAX_BACK_W,
                waste=waste, scale=L["cssW"] / GAME_W)


# ── 난수 — 게임의 Math.random() 과 같지 않다. 결정적으로 만들 뿐이다 ──
class RNG(object):
    def __init__(self, seed=1):
        self.s = (seed * 1103515245 + 12345) & 0x7FFFFFFF

    def __call__(self):
        self.s = (self.s * 1103515245 + 12345) & 0x7FFFFFFF
        return self.s / float(0x7FFFFFFF)


# ── 게임 ──────────────────────────────────────────────────────────────
class Sim(object):
    """`game/index.html` 의 상태·전투·저장·오프라인을 옮긴 것.

    그리기와 입력은 없다. `now_ms` 는 `Date.now()` 자리다."""

    def __init__(self, seed=1, state=None, now_ms=None):
        self.rnd = RNG(seed)
        self.now_ms = DEFAULT_NOW_MS if now_ms is None else now_ms
        self.G = state if state is not None else self.freshState()
        self.zombies = []
        self.shots = 0                 # 궤적은 그리기용이라 개수만 센다
        self.spawnTimer = 0.0
        self.attackTimer = 0.0
        self.killIndex = 0
        self.t = 0.0
        self.reviveOffer = None      # {"zone": 죽은 구역, "t": 흐른 시간}
        self.dmgBank = 0.0           # 좀비가 없어 남은 초과 피해. 다음 좀비에게 얹는다
        self.deaths = 0              # 포트에만 있는 계수기. 원본에는 없다
        self.offlineReport = None
        self.adLog = []
        self.tab = "stat"
        self.listScroll = 0.0
        self.listMax = 0.0

    # ---- 저장 ----
    def freshState(self):
        return dict(v=SAVE_VERSION, parts=0.0, plans=0.0, zone=1, kills=0,
                    gear={}, bag=[], day=0, maxDay=0, quest=dict(zone=0, up=0, stage=0), questTaken={},
                    login=dict(streak=0, lastDay=-1), keys=KEY_MAX,
                    lv=dict(atk=0, spd=0, hp=0, reg=0, inc=0), weapon="pipe",
                    owned=dict(pipe=1), hp=100.0, bestZone=1, totalKills=0,
                    lastSeen=self.now_ms, boostUntil=0)

    def migrate(self, raw):
        if not isinstance(raw, dict):
            return self.freshState()
        if raw.get("v") == 1:
            raw = dict(raw, v=2, bestZone=max(raw.get("bestZone") or 1, raw.get("zone") or 1))
        if raw.get("v") == 2:
            raw = dict(raw, v=3, plans=0.0)   # M3 5: 설계도가 생겼다
        if raw.get("v") == 3:                 # M4 1: 일일 리듬이 생겼다
            raw = dict(raw, v=4, day=0, maxDay=0,
                       quest=dict(zone=0, up=0, stage=0), questTaken={},
                       login=dict(streak=0, lastDay=-1), keys=KEY_MAX)
        if raw.get("v") != SAVE_VERSION:
            return self.freshState()
        s = self.freshState()
        for k in list(s.keys()):
            if k in raw:
                s[k] = raw[k]
        # 옛 저장본에는 inc 가 없다. 0 으로 채운다 (원본과 같다)
        lv = dict(atk=0, spd=0, hp=0, reg=0, inc=0)
        lv.update(raw.get("lv") or {})
        s["lv"] = lv
        ow = dict(pipe=1)
        ow.update(raw.get("owned") or {})
        s["owned"] = ow
        return s

    # ---- 파생 ----
    def statDef(self, i):
        return next(s for s in STATS if s["id"] == i)

    def statOf(self, i):
        s = self.statDef(i)
        return s["base"] * (s["growth"] ** self.G["lv"].get(i, 0)) * self.gearMult(i)

    def statCost(self, i):
        s = self.statDef(i)
        return math.ceil(s["cost0"] * (s["costG"] ** self.G["lv"].get(i, 0)))

    def weaponOf(self, i):
        return next(w for w in WEAPON_TYPES if w["id"] == i)

    def weaponPower(self):
        w = self.weaponOf(self.G["weapon"])
        tier = self.G["owned"].get(self.G["weapon"], 1)
        return w["mult"] * (1 + TIER_POWER * (tier - 1))

    def hitDamage(self):
        return self.statOf("atk") * self.weaponPower()

    def attacksPerSec(self):
        """M4 2 — 원본과 **같은 구조**로 옮긴다: 집중 사격 중이면 x FOCUS_MULT.
           다만 시뮬의 기본은 `self.focus = False` 다 — 사람이 탭해야 켜지는 것이라
           `auto_run` 은 '안 누르는 쪽' 을 잰다. 그게 M4-B2 의 기준선이다.
           **배수를 아예 안 옮기면** 나중에 원본이 바뀌어도 c16 이 못 잡는다. 그래서 구조를 옮긴다."""
        return self.statOf("spd") * (FOCUS_MULT if getattr(self, "focus", False) else 1)

    def playerDPS(self):
        return self.hitDamage() * self.attacksPerSec()

    def maxHP(self):
        return self.statOf("hp")

    def regenPerSec(self):
        return self.statOf("reg")

    @staticmethod
    def zoneHP(z):
        return ZONE_HP0 * (ZONE_HP_G ** (z - 1))

    @staticmethod
    def zoneDPS(z):
        return Sim.zoneHP(z) * ZOMBIE_DPS_RATIO

    @staticmethod
    def stageKills(z):
        return max(1, jsround(Sim.zoneKills(z) / STAGES_PER_ZONE))

    @staticmethod
    def killReward(z):
        return Sim.zoneReward(z)

    @staticmethod
    def zoneIncome(z):
        return Sim.zoneReward(z) * Sim.zoneKills(z)

    def rollTier(self, z):
        center = 1 + (TIER_MAX_PORT - 1) * min(1.0, (z - 1) / float(ZONE_COUNT - 1))
        t = jsround(center + (self.rnd() + self.rnd() + self.rnd() - 1.5) * 1.6)
        return max(1, min(TIER_MAX_PORT, t))

    def rollGear(self, z):
        armor = GEAR_SLOT_IDS[1:]
        slot = armor[int(self.rnd() * len(armor))]
        tier = self.rollTier(z)
        shape = int(self.rnd() * GEAR_SHAPES)
        n_aff = min(GEAR_AFFIXES, 2 if self.rnd() < (tier - 1) / float(TIER_MAX_PORT - 1) else 1)
        pool = list(AFFIX_IDS)
        affixes = []
        for _ in range(n_aff):
            if not pool:
                break
            k = int(self.rnd() * len(pool))
            aid = pool.pop(k)
            affixes.append({"id": aid, "mult": 1 + AFFIX_PER[aid] * tier * (0.7 + self.rnd() * 0.6)})
        return {"slot": slot, "shape": shape, "tier": tier, "affixes": affixes, "zone": z}

    @staticmethod
    def gearScore(g):
        if not g:
            return 0.0
        v = math.pow(2.1, g["tier"] - 1)
        for a in g["affixes"]:
            v *= a["mult"]
        return v

    def gearMult(self, sid):
        m = 1.0
        for slot in GEAR_SLOT_IDS:
            g = (self.G.get("gear") or {}).get(slot)
            if not g:
                continue
            for a in g["affixes"]:
                if a["id"] == sid:
                    m *= a["mult"]
        return m

    def _income(self, kind, v):
        """**측정용 계수기.** 원본 게임에는 없다 — 그래서 MIRRORED 대상이 아니다.
           부품이 어디서 들어왔는지 나눠 센다 (M4 4.1 / M4-B3)."""
        d = getattr(self, "income", None)
        if d is None:
            d = self.income = {"kill": 0.0, "sell": 0.0}
        d[kind] = d.get(kind, 0.0) + v

    def gearSellPrice(self, g):
        return (self.zoneIncome(g.get("zone") or self.G["zone"]) * 0.09
                * math.pow(1.55, g["tier"] - 1) * self.statOf("inc"))

    def dropGear(self, g):
        self.G.setdefault("gear", {})
        self.G.setdefault("bag", [])
        if not self.G["gear"].get(g["slot"]):
            self.G["gear"][g["slot"]] = g
            return "equip"
        if ((self.G.get("bestZone") or 1) >= AUTOSELL_ZONE
                and g["tier"] <= max(0, min(TIER_MAX_PORT - 1, self.G.get("autoSell") or 0))):
            v = self.gearSellPrice(g)
            self.G["parts"] += v
            self._income("sell", v)                     # M4 4.2
            return "autosell"
        self.G["bag"].append(g)
        if len(self.G["bag"]) > BAG_MAX:
            self.G["bag"].sort(key=lambda x: self.gearScore(x))
            v = self.gearSellPrice(self.G["bag"].pop(0))
            self.G["parts"] += v
            self._income("sell", v)
        return "bag"

    @staticmethod
    def stageBlueprint(z):
        return Sim.zoneIncome(z) * BP_RATIO * BP_STAGE_SHARE / (STAGES_PER_ZONE - 1)

    @staticmethod
    def bossBlueprint(z):
        return Sim.zoneIncome(z) * BP_RATIO * BP_BOSS_SHARE

    @staticmethod
    def zoneKills(z):
        return KILLS_PER_ZONE * (WALL_KILL_MULT if (z >= WALL_START and z % WALL_EVERY == 0) else 1)   # M2 벽: 구역 10 부터, 처치 수만

    @staticmethod
    def zoneReward(z):
        return ZONE_RW0 * (ZONE_RW_G ** (z - 1)) * KILLS_PER_ZONE / Sim.zoneKills(z)   # M2 벽: 처치당 보상 ÷3

    @staticmethod
    def isBossKill(z, idx):
        return (z % BOSS_EVERY == 0) and idx == Sim.zoneKills(z) - 1

    def weaponUnlocked(self, w):
        return w.get("unlock", 1) <= self.G.get("bestZone", 1)

    def weaponUpgradeCost(self, wid):
        w = self.weaponOf(wid)
        tier = self.G["owned"].get(wid, 0)
        if not self.weaponUnlocked(w):
            return None
        if tier == 0:
            return w["cost"]
        if tier >= TIER_MAX:
            return None
        return math.ceil(max(w["cost"], 400) * (TIER_COST_MULT ** tier))

    def boostActive(self):
        return self.now_ms < (self.G.get("boostUntil") or 0)

    def rewardMult(self):
        return 2 if self.boostActive() else 1

    # ---- 구매 ----
    def questBand(self, hour):
        return 2 if (hour >= QUEST_BANDS[2] or hour < QUEST_BANDS[0]) else (1 if hour >= QUEST_BANDS[1] else 0)

    def questOpen(self, q):
        # 원본은 로컬 시각(getHours). 포트는 now_ms 의 UTC 시각 — 시간대 **번호**가 같으면 된다.
        return self.questBand(int((self.now_ms // 3600000) % 24)) == int(q["band"])

    def questProgress(self, qid, n):
        """M4 1 — 카운터만 센다. **시뮬은 일일 보상을 수령하지 않는다** (사람이 눌러야 받는다).
           그래서 auto_run 의 진행에 일일 보상이 안 섞이고 곡선 측정이 흔들리지 않는다.
           M4 1.2 (a): 열린 시간대에만 센다."""
        q = next((x for x in QUEST_DEFS if x["id"] == qid), None)
        if q is not None and not self.questOpen(q):
            return
        d = self.G.setdefault("quest", {})
        d[qid] = d.get(qid, 0) + n

    # ---- 일일 보상 (M4 1) ----
    # **2026-09-16 에 옮겼다.** 전에는 이 넷이 포트에 없어서 `auto_run` 이 일일 보상을
    # 한 번도 안 받았다. 그래서 WBS 1.4 의 판정 문구("20시드 구역 30 도달이 ±5% 안")가
    # **실패할 수 없는 시험**이었다 — 받은 적이 없으니 차이가 늘 0.0% 다.
    # 브라우저로 따로 잰 daily-budget 기록도 `dailyBudget() x 몫` 을 다시 계산한 것이라
    # 비율이 늘 `DAILY_BUDGET x 몫합` 으로 나오는 **항등식**이었다 (사례 12 와 같은 부류).
    # 이제 실제로 받게 해서 잰다.
    def dayIndex(self, ms):
        return int(ms // DAY_MS)

    def dailyBudget(self):
        return self.partsPerSecondEstimate() * 3600 * DAILY_BUDGET

    def grant(self, gain):
        """원본의 지급 두 줄 — 부품과 설계도를 같이 준다."""
        self.G["parts"] += gain
        self.G["plans"] = self.G.get("plans", 0.0) + gain * BP_RATIO
        return gain

    def rolloverDay(self):
        today = self.dayIndex(self.now_ms)
        if today <= (self.G.get("maxDay") or 0):
            if today > (self.G.get("day") or 0):
                self.G["day"] = today
            return None
        prev = self.G.get("login") or {"streak": 0, "lastDay": -1}
        cont = prev.get("lastDay") == today - 1
        self.G["login"] = {"streak": min(LOGIN_DAYS, prev.get("streak", 0) + 1) if cont else 1,
                           "lastDay": today}
        self.G["quest"] = {"zone": 0, "up": 0, "stage": 0}
        self.G["questTaken"] = {}
        self.G["keys"] = KEY_MAX
        self.G["day"] = today
        self.G["maxDay"] = today
        w = LOGIN_SHARES[self.G["login"]["streak"] - 1] if self.G["login"]["streak"] - 1 < len(LOGIN_SHARES) else LOGIN_SHARES[0]
        gain = self.grant(self.dailyBudget() * w)
        return {"kind": "login", "day": self.G["login"]["streak"], "gain": gain}

    def questReady(self, qid):
        return (self.G.get("quest", {}).get(qid, 0) >= QUEST_NEEDS[qid]
                and not (self.G.get("questTaken") or {}).get(qid))

    def takeQuest(self, qid):
        if not self.questReady(qid):
            return False
        self.G.setdefault("questTaken", {})[qid] = 1
        return self.grant(self.dailyBudget() * QUEST_SHARES[qid])

    def openSupply(self):
        if (self.G.get("keys") or 0) <= 0:
            return False
        self.G["keys"] -= 1
        return self.grant(self.dailyBudget() * SUPPLY_SHARE / KEY_MAX)

    def buyStat(self, i):
        if i in GEAR_ONLY_STATS:                 # M4 4.3
            return False
        c = self.statCost(i)
        if self.G["parts"] < c:
            return False
        self.G["parts"] -= c
        self.G["lv"][i] = self.G["lv"].get(i, 0) + 1
        self.questProgress("up", 1)
        return True

    def buyWeapon(self, wid):
        cost = self.weaponUpgradeCost(wid)
        if cost is None or self.G.get("plans", 0.0) < cost:   # M3 5: 무기는 설계도로만
            return False
        self.G["plans"] = self.G.get("plans", 0.0) - cost
        self.G["owned"][wid] = self.G["owned"].get(wid, 0) + 1
        self.G["weapon"] = wid
        self.questProgress("up", 1)
        return True

    def equip(self, wid):
        if self.G["owned"].get(wid):
            self.G["weapon"] = wid
            return True
        return False

    # ---- 버튼 배치 ----
    def tabRowY(self):
        return L["PANEL_TOP"]

    def listTopY(self):
        return L["PANEL_TOP"] + ROW_H + 8

    def adRowY(self):
        return L["GAME_H"] - ROW_H - 10

    def listBotY(self):
        return self.adRowY() - 8

    def buildButtons(self):
        """원본 `buildButtons()` 의 **자리와 상태만** 옮긴 것.

        글자(label/sub)는 그리기용이라 옮기지 않는다. 대신 `kind` 로 무엇인지 구분한다.
        7.1(탭 대상 크기) · 7.2(한 화면 공존) · 5.2(팝업만 남는지) 를 이걸로 잰다.
        지시 #46 으로 탭 2개 -> 스크롤 목록 하나가 됐다."""
        bs = []
        self.headers = []

        def b(kind, x, y, w, h, tone, enabled=True, wid=None, clip=None):
            bs.append(dict(kind=kind, x=x, y=y, w=w, h=h, tone=tone,
                           enabled=enabled, wid=wid, clip=clip))

        if self.offlineReport:
            b("scrim", 0, 0, GAME_W, L["GAME_H"], "scrim")
            if not self.offlineReport.get("doubled"):
                b("offline2x", 90, L["GAME_H"] / 2 + 40, 360, ROW_H, "ad")
            b("offline_close", 150, L["GAME_H"] / 2 + 108, 240, ROW_H, "ghost")
            return bs

        # M4 1 — 탭 3개. 폭 164, 간격 8 (원본과 같다)
        TW, TG = 120, 6                       # M4 3.4: 탭 4개
        for i, tid in enumerate(("stat", "weapon", "gear", "daily")):
            b("tab_" + tid, 24 + i * (TW + TG), self.tabRowY(), TW, ROW_H,
              "on" if self.tab == tid else "off")

        top, bot = self.listTopY(), self.listBotY()
        clip = (top, bot)
        cy = [0.0]

        def put_row(kind, tone, enabled, wid):
            y = top + cy[0] - self.listScroll
            cy[0] += ROW_PITCH
            if y + ROW_H < top or y > bot:
                return
            b(kind, 24, y, GAME_W - 48, ROW_H, tone, enabled, wid, clip)

        if self.tab == "gear":
            for sl in GEAR_SLOT_IDS:
                put_row("gear_slot", "ghost", False, sl)
            bag = self.G.get("bag") or []
            if not bag:
                put_row("bag_empty", "ghost", False, None)
            for g in sorted(bag, key=lambda x: -self.gearScore(x)):
                cur = (self.G.get("gear") or {}).get(g["slot"])
                better = self.gearScore(g) > self.gearScore(cur)
                put_row("bag_item", "buy" if better else "off", True, g["slot"])
        elif self.tab == "daily":
            # M4 1 — 접속 1줄 + 과제 3줄 + 보급 상자 1줄
            put_row("login", "ghost", False, None)
            for q in QUEST_DEFS_IDS:
                cur = (self.G.get("quest") or {}).get(q, 0)
                need = QUEST_NEEDS[q]
                taken = bool((self.G.get("questTaken") or {}).get(q))
                put_row("quest", "ghost" if taken else ("buy" if cur >= need else "off"),
                        (not taken) and cur >= need, q)
            keys = self.G.get("keys", 0)
            put_row("supply", "buy" if keys > 0 else "off", keys > 0, None)
        elif self.tab == "stat":
            for s in [x for x in STATS if x["id"] not in GEAR_ONLY_STATS]:   # M4 4.3
                cost = self.statCost(s["id"])
                put_row("stat", "buy", self.G["parts"] >= cost, s["id"])
        else:
            locked_shown = [False]
            for w in WEAPON_TYPES:
                if not self.weaponUnlocked(w):
                    if not locked_shown[0]:
                        locked_shown[0] = True
                        put_row("weapon_locked", "ghost", False, w["id"])
                    continue
                tier = self.G["owned"].get(w["id"], 0)
                cost = self.weaponUpgradeCost(w["id"])
                maxed = tier >= TIER_MAX
                put_row("weapon", "equipped" if self.G["weapon"] == w["id"] else "buy",
                        tier > 0 or ((not maxed) and cost is not None and self.G.get("plans", 0.0) >= cost), w["id"])   # 가진 무기는 언제나 눌린다 (지시 #70). M3 5: 설계도로 판정

        self.listMax = max(0.0, cy[0] - (bot - top))
        self.listScroll = min(max(0.0, self.listScroll), self.listMax)

        b("ad_boost", 24, self.adRowY(), GAME_W - 48, ROW_H, "ad", not self.boostActive())

        if self.reviveOffer:
            b("revive_ad", 90, L["ARENA_BOT"] - 70, 360, ROW_H, "ad")
        return bs

    def hitButton(self, px, py, bs=None):
        bs = self.buildButtons() if bs is None else bs
        css_per = (L.get("cssW") or GAME_W) / float(GAME_W)   # fit_game 전엔 cssW 가 0.0 이라 or 로 1 (16차 감사 지적)
        for b in reversed(bs):
            top = max(b["y"], b["clip"][0]) if b.get("clip") else b["y"]
            bot = min(b["y"] + b["h"], b["clip"][1]) if b.get("clip") else b["y"] + b["h"]
            # 잘려서 판정선보다 얇아진 줄은 탭 대상이 아니다 (원본과 같은 규칙)
            if b.get("clip") and (bot - top) * css_per < min(MIN_TAP_CSS, b["h"] * css_per) - 1e-9:
                continue
            if b["x"] <= px <= b["x"] + b["w"] and top <= py <= bot:
                return b
        return None

    # ---- 전투 ----
    def spawnZombie(self):
        if len(self.zombies) >= MAX_ONSCREEN_ZOMBIES:
            return
        boss = self.isBossKill(self.G["zone"], self.killIndex + len(self.zombies))
        hp = self.zoneHP(self.G["zone"]) * (BOSS_HP_MULT if boss else 1)
        # 난수를 원본과 **같은 개수·같은 순서**로 뽑는다.
        # 원본은 x → y → (보스가 아닐 때만) speed → wob 순이다.
        # 개수가 다르면 수열이 어긋나 시드별 값이 원본 구조와 달라진다 (9차 감사 지적).
        x = SPAWN_X + self.rnd() * 30
        y = L["GROUND_Y"] - self.rnd() * 12
        speed = 17.0 if boss else 24 + self.rnd() * 12
        wob = self.rnd() * 6
        self.zombies.append(dict(
            x=x, y=y, hp=hp, max=hp, boss=boss, speed=speed, wob=wob,
            held=False, charge=0.0,
            nextCharge=BOSS_CHARGE_EVERY if boss else 0.0))

    def damageZombie(self, z, dmg):
        z["hp"] -= dmg
        if z["hp"] <= 0:
            self.killZombie(z)

    def applyDamage(self, dmg):
        left, guard = dmg + self.dmgBank, 0
        self.dmgBank = 0.0
        while left > 1e-9 and self.zombies and guard < MAX_ONSCREEN_ZOMBIES + 2:
            guard += 1
            target, best = None, 1e9
            for z in self.zombies:
                if z["x"] < best:
                    best, target = z["x"], z
            if target is None:
                break
            take = min(left, target["hp"])
            left -= take
            self.damageZombie(target, take)
        if left > 1e-9:
            self.dmgBank = left

    def killZombie(self, z):
        # 원본 `indexOf` 는 **참조** 동일성이다. `in` / `remove` 는 값 동일성이라
        # 필드가 전부 같은 좀비가 둘이면 다른 마리를 지운다 (9차 감사 지적).
        i = next((k for k, x in enumerate(self.zombies) if x is z), -1)
        if i < 0:
            return
        del self.zombies[i]
        # 원본은 파편을 정상 7개·보스 16개 만들고 각각 난수를 3번(vx, vy, life) 뽑는다.
        # 안 뽑으면 그 뒤 수열이 통째로 어긋난다 — 12차 감사가 t=4.05초에 갈리는 것을 잡았다.
        for _ in range(3 * (16 if z["boss"] else 7)):
            self.rnd()
        gain = (self.killReward(self.G["zone"]) * (BOSS_EVERY if z["boss"] else 1)
                * self.rewardMult() * self.statOf("inc"))
        self.G["parts"] += gain
        self._income("kill", gain)
        self.G["totalKills"] += 1
        self.killIndex += 1
        # M3 4.2 — 단계 클리어 일시금. 구역을 넘는 마지막 칸에서는 안 준다.
        if (self.killIndex % self.stageKills(self.G["zone"]) == 0
                and self.killIndex < self.zoneKills(self.G["zone"])):
            self.questProgress("stage", 1)
            self.dropGear(self.rollGear(self.G["zone"]))   # M4 3.4
            self.G["plans"] = self.G.get("plans", 0.0) + (
                self.stageBlueprint(self.G["zone"]) * self.rewardMult() * self.statOf("inc"))
        if z["boss"]:
            self.G["plans"] = self.G.get("plans", 0.0) + (
                self.bossBlueprint(self.G["zone"]) * self.rewardMult() * self.statOf("inc"))
        if self.killIndex >= self.zoneKills(self.G["zone"]):
            self.killIndex = 0
            if self.G["zone"] < ZONE_COUNT:
                self.G["zone"] += 1
                self.questProgress("zone", 1)
                self.G["bestZone"] = max(self.G["bestZone"], self.G["zone"])
                del self.zombies[:]
                self.shots = 0
        self.G["kills"] = self.killIndex

    def stepCombat(self, dt):
        hadTarget = len(self.zombies) > 0

        self.spawnTimer -= dt
        ttk = self.zoneHP(self.G["zone"]) / max(1e-6, self.playerDPS())
        spawnGap = min(2.0, max(0.35, ttk * 0.9))
        remaining = self.zoneKills(self.G["zone"]) - self.killIndex   # M2: 벽 구역은 처치 수 x3
        if self.spawnTimer <= 0 and len(self.zombies) < min(MAX_ONSCREEN_ZOMBIES, remaining):
            self.spawnZombie()
            self.spawnTimer = spawnGap

        contactDPS = 0.0
        self.zombies.sort(key=lambda z: z["x"])
        for i, z in enumerate(self.zombies):
            if z["boss"]:
                if z["charge"] > 0:
                    z["charge"] -= dt
                z["nextCharge"] -= dt
                if z["nextCharge"] <= 0:
                    z["charge"] = BOSS_CHARGE_TIME
                    z["nextCharge"] = BOSS_CHARGE_EVERY
            spd = z["speed"] * (BOSS_CHARGE_MULT if z["charge"] > 0 else 1)
            stopX = CONTACT_X + i * ZOMBIE_GAP
            if z["x"] > stopX + 0.5:
                z["x"] = max(stopX, z["x"] - spd * dt)
                z["held"] = False
            else:
                z["x"] = stopX
                z["held"] = True
            if z["x"] <= CONTACT_X + CONTACT_REACH + 0.5:
                contactDPS += self.zoneDPS(self.G["zone"]) * (2 if z["boss"] else 1)

        interval = 1.0 / max(0.05, self.attacksPerSec())
        if not hadTarget:
            self.attackTimer = interval
        else:
            self.attackTimer -= dt
        guard = 0
        while self.attackTimer <= 0 and self.zombies and guard < 40:
            guard += 1
            self.attackTimer += interval
            target, best = None, 1e9
            for z in self.zombies:
                if z["x"] < best:
                    best, target = z["x"], z
            if target is not None:
                self.shots += 1
                self.applyDamage(self.hitDamage())
        if not self.zombies:
            self.attackTimer = interval

        self.G["hp"] = min(self.maxHP(),
                           self.G["hp"] + self.regenPerSec() * dt - contactDPS * dt)
        if self.G["hp"] <= 0:
            self.onDeath()
        if self.reviveOffer:
            self.reviveOffer["t"] += dt
            if self.reviveOffer["t"] >= REVIVE_OFFER_SEC:
                self.reviveOffer = None

    def onDeath(self):
        """쓰러지면 한 구역 물러나 계속 싸운다 (지시 #35). 멈추지 않는다."""
        self.deaths += 1
        self.G["hp"] = self.maxHP()
        del self.zombies[:]
        self.shots = 0
        frm = self.G["zone"]
        if self.G["zone"] > 1:
            self.G["zone"] -= 1
        self.killIndex = 0
        self.G["kills"] = 0
        self.reviveOffer = {"zone": frm, "t": 0.0}

    def acceptRevive(self):
        """광고를 보면 죽은 그 구역으로 돌아간다."""
        if not self.reviveOffer:
            return False
        self.G["zone"] = min(ZONE_COUNT, self.reviveOffer["zone"])
        self.G["bestZone"] = max(self.G["bestZone"], self.G["zone"])
        self.G["hp"] = self.maxHP()
        self.killIndex = 0
        self.G["kills"] = 0
        del self.zombies[:]
        self.shots = 0
        self.reviveOffer = None
        return True

    def step(self, dt):
        """`frame()` 의 고정 시간 간격 한 칸. 시계도 같이 민다."""
        self.stepCombat(dt)
        self.t += dt
        self.now_ms += dt * 1000

    # ---- 오프라인 ----
    def partsPerSecondEstimate(self):
        ttk = self.zoneHP(self.G["zone"]) / max(1e-6, self.playerDPS())
        return self.zoneReward(self.G["zone"]) * self.statOf("inc") / max(ttk, 0.35)

    def applyOffline(self):
        elapsed = max(0.0, (self.now_ms - (self.G.get("lastSeen") or self.now_ms)) / 1000.0)
        capped = min(elapsed, OFFLINE_MAX_HOURS * 3600)
        if capped < 60:
            return None
        gain = self.partsPerSecondEstimate() * capped * OFFLINE_RATE
        self.G["parts"] += gain
        # M3 5 — 설계도도 같이 쌓인다 (원본과 같다)
        bp = gain * BP_RATIO * BP_OFFLINE_SHARE
        self.G["plans"] = self.G.get("plans", 0.0) + bp
        return dict(elapsed=elapsed, capped=capped, gain=gain, plans=bp,
                    cappedHit=elapsed > capped + 1, doubled=False)


# ── 자동구매 1런 — 감사가 매번 다시 짜던 절차를 여기 고정한다 ────────
def auto_run(seed=1, max_min=120, buy_every=0.5, dt=FIXED_STEP,
             offline_every_min=None, offline_hours=8, on_buy=None, focus_duty=None,
             stop_zone=None, now_ms=None):
    """가장 싼 것부터 계속 사면서 구역 10 까지 간다.

    `offline_every_min` 을 주면 그만큼 놀고 나서 `offline_hours` 시간 자리를 비운다.
    예측 B4(오프라인 계수를 2배로 바꿔도 진행이 20% 넘게 흔들리지 않는다)를 재는 데 쓴다.

    `on_buy(t초, 구역, 산것, 값)` 을 주면 살 때마다 부른다 — 업그레이드 간격을 재는 데 쓴다.
    `focus_duty=(3, 20)` 을 주면 20초마다 3초씩 집중 사격을 켠다 (M4 2).

    돌아오는 값: 구역별 도달 시각(분) · 벽(10분 넘게 정체한 구역) · 사망 수 · 총 분."""
    s = Sim(seed=seed, now_ms=now_ms)     # now_ms: 시간대 과제를 재려고 시작 시각을 옮길 때만 (tools/quest_pace.py)
    s.G["hp"] = s.maxHP()
    zone_at, wall = {1: 0.0}, {}
    deaths, buyT, stuck_from, last_zone = 0, 0.0, 0.0, 1
    idle_buy = 0          # 살 수 있는데 안 산 매수 틱 (c22 가 읽는다)
    # 사망은 이제 Sim 안에서 처리된다(자동 후퇴). 여기서는 세기만 한다.
    off_t, off_n, off_gain = 0.0, 0, 0.0
    # stop_zone 을 주면 그 구역에 닿는 순간 멈추고 **Sim 을 그대로 돌려준다.**
    # 다른 도구가 "구역 z 에 있는 진짜 상태" 를 필요로 할 때 쓴다 (tools/daily_budget.py).
    # 여기서 멈추게 하는 이유: 매수 줄을 도구마다 새로 짜면 **자가 둘이 되어** 갈라진다.
    # 2026-09-16 에 바로 그 방식으로 이틀을 잃었다 (cases/2026-09-16-22).
    limit = ZONE_COUNT if stop_zone is None else min(stop_zone, ZONE_COUNT)
    while s.t < max_min * 60 and s.G["zone"] < limit:
        # M4 2 — focus_duty=(켜는 초, 주기 초) 를 주면 **쿨타임을 지키며** 집중 사격을 켠다.
        # 사람이 가장 부지런히 눌렀을 때를 모사한 것이다. 기본은 None = 안 누름.
        if focus_duty:
            on_s, period_s = focus_duty
            s.focus = (s.t % period_s) < on_s
        s.step(dt)
        deaths = s.deaths
        if offline_every_min:
            off_t += dt
            if off_t >= offline_every_min * 60:
                off_t = 0.0
                s.G["lastSeen"] = s.now_ms - offline_hours * 3600 * 1000
                r = s.applyOffline()
                if r:
                    off_n += 1
                    off_gain += r["gain"]
                s.G["lastSeen"] = s.now_ms
        buyT += dt
        if buyT >= buy_every:
            buyT = 0.0
            # **재화가 둘이면 줄도 둘이다.** (2026-09-16, 지시 #102)
            # 전에는 무기 값도 `parts` 와 견주고 결제는 `plans` 로 했다.
            # 그래서 못 살 무기가 "가장 싼 것" 으로 뽑히면 그 틱이 통째로 멈췄고,
            # 살 수 있는 능력치까지 건너뛰었다. 구역 29 에서 **부품 98억을 안 쓰고
            # 쌓아 둔 채 3180틱을 헛돌았다.** 사람이 그렇게 놀 리가 없다.
            # 값을 통화끼리 견주는 것 자체가 뜻이 없다 — 부품을 아껴 무기를 살 수 없다.
            # 그래서 **각 재화 안에서만** 싼 것부터 산다. 게임 화면은 처음부터 이랬다
            # (game/index.html 의 무기 버튼은 `G.plans >= cost` 로 켜진다).
            bought = True
            while bought:
                bought = False

                bid, cheap = None, float("inf")          # 능력치 — 부품
                for st in STATS:
                    if st["id"] in GEAR_ONLY_STATS:
                        continue          # 못 사는 축은 후보도 아니다 — 아래 주석
                    c = s.statCost(st["id"])
                    if c <= s.G["parts"] and c < cheap:
                        cheap, bid = c, st["id"]
                # **거부당할 후보가 남을 막으면 안 된다.** (2026-09-16 두 번째)
                # 2026-09-15 4.3 실험은 hp·reg 를 GEAR_ONLY_STATS 로 막고 돌렸는데, 이 루프가
                # 그 둘을 후보에서 안 뺐다. hp 가 "가장 싼 것" 으로 뽑히면 buyStat 이 False 를 내고
                # 그 틱의 능력치 매수가 통째로 끝났다 — atk·spd·inc 를 살 수 있는데도.
                # 그래서 "진행이 통째로 막혔다" 가 나왔다. 통화 버그와 같은 부류다:
                # 고르는 줄과 결제하는 줄이 어긋나면 가짜 사람이 돈을 쥐고 논다.
                # 고친 자로 다시 돌리니 헛돈틱 836,040 이 그것을 드러냈다 (cases/2026-09-16-22).
                if bid and s.buyStat(bid):
                    bought = True
                    # on_buy 를 주면 산 것을 하나씩 알려준다 (tools/upgrade_cadence.py).
                    # 기본은 None 이라 curve_check 등 기존 호출은 그대로다.
                    if on_buy:
                        on_buy(s.t, s.G["zone"], bid, cheap)

                wid, wcheap = None, float("inf")         # 무기 — 설계도
                for w in WEAPON_TYPES:
                    c = s.weaponUpgradeCost(w["id"])
                    if c is not None and c <= s.G.get("plans", 0.0) and c < wcheap:
                        wcheap, wid = c, w["id"]
                if wid and s.buyWeapon(wid):
                    bought = True
                    if on_buy:
                        on_buy(s.t, s.G["zone"], "W:" + wid, wcheap)

            # **자가 고장 났는지 자기가 센다.** 매수를 끝낸 직후에는 살 수 있는 게
            # 하나도 남아 있으면 안 된다 — 남았다면 이 가짜 사람이 돈을 쥐고 안 쓴 것이다.
            # 2026-09-16 에 바로 그 일이 이틀 동안 조용히 있었다 (cases/2026-09-16-22).
            # checks/c22 가 이 수를 읽는다. 여기서 세는 이유는 **매수 줄이 하나뿐이어야**
            # 검사와 도구가 갈라지지 않기 때문이다.
            if any(s.statCost(st["id"]) <= s.G["parts"]
                   for st in STATS if st["id"] not in GEAR_ONLY_STATS):
                idle_buy += 1
            else:
                for w in WEAPON_TYPES:
                    c = s.weaponUpgradeCost(w["id"])
                    if c is not None and c <= s.G.get("plans", 0.0):
                        idle_buy += 1
                        break
        if s.G["zone"] != last_zone:
            if s.t - stuck_from > 600:
                wall[last_zone] = round((s.t - stuck_from) / 60)
            last_zone, stuck_from = s.G["zone"], s.t
        if s.G["zone"] not in zone_at:
            zone_at[s.G["zone"]] = s.t
    if s.t - stuck_from > 600:
        wall[s.G["zone"]] = round((s.t - stuck_from) / 60)
    return dict(zone_min={z: round(v / 60, 1) for z, v in sorted(zone_at.items())},
                wall=wall, deaths=deaths, total_min=round(s.t / 60, 1),
                final_zone=s.G["zone"], offline_n=off_n, offline_gain=off_gain,
                idle_buy=idle_buy, sim=s)


# ── 자기 점검 ─────────────────────────────────────────────────────────
def _reseal():
    names = sorted(MIRRORED.keys())
    seals = {n: fingerprint(n) for n in names}
    p = os.path.abspath(__file__)
    txt = io.open(p, encoding="utf-8").read()
    block = "MIRRORED = {\n" + "".join(
        '    "%s": "%s",\n' % (n, seals[n]) for n in names) + "}"
    txt = re.sub(r"MIRRORED = \{.*?\n\}", lambda m: block, txt, flags=re.S)
    io.open(p, "w", encoding="utf-8").write(txt)
    print("해시 %d개를 다시 찍었다. git diff 로 무엇이 바뀌었는지 사람이 본다." % len(names))


def _selfcheck():
    d = drift()
    print("원본 대조: %s" % ("어긋난 함수 %d개" % len(d) if d else "옮긴 함수 %d개 전부 일치" % len(MIRRORED)))
    for n, want, got in d:
        print("  - %s  잠금 %s  현재 %s" % (n, want, got))
    print("상수: 구역 %d / 무기 %d / 능력치 %d / 좀비상한 %d / ZOMBIE_DPS_RATIO %s"
          % (ZONE_COUNT, len(WEAPON_TYPES), len(STATS), MAX_ONSCREEN_ZOMBIES, ZOMBIE_DPS_RATIO))
    s = Sim(seed=1)
    s.G["hp"] = s.maxHP()
    for _ in range(60 * 60):
        s.step(FIXED_STEP)
    print("60초 런(seed 1): 구역 %d / 처치 %d / 부품 %.1f / hp %.2f / 사망 %d"
          % (s.G["zone"], s.G["totalKills"], s.G["parts"], s.G["hp"], s.deaths))
    return 1 if d else 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if "--reseal" in sys.argv:
        _reseal()
    else:
        sys.exit(_selfcheck())
