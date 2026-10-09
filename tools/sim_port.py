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

def vector(name):
    """`const NAME = [\n  a, b, c\n];` (숫자 목록) 를 읽는다 — M6 7.2 GACHA_XP_NEEDS."""
    mm = re.search(r"const\s+" + name + r"\s*=\s*\[(.*?)\n\];", SRC, re.S)
    if not mm:
        raise ValueError("game/index.html 에서 목록 %s 를 못 찾았다" % name)
    return [float(v) for v in re.findall(r"-?[\d.]+", re.sub(r"//[^\n]*", "", mm.group(1)))]


def matrix(name):
    """`const NAME = [ [..], [..] ];` (숫자 행렬) 를 읽는다 — M6 2.2 TIER_ODDS."""
    mm = re.search(r"const\s+" + name + r"\s*=\s*\[(.*?)\n\];", SRC, re.S)
    if not mm:
        raise ValueError("game/index.html 에서 행렬 %s 를 못 찾았다" % name)
    body = re.sub(r"//[^\n]*", "", mm.group(1))
    return [[float(v) for v in re.findall(r"-?[\d.]+", row)] for row in re.findall(r"\[([^\[\]]*)\]", body)]

TIER_ODDS = matrix("TIER_ODDS")
GACHA_XP_NEEDS = vector("GACHA_XP_NEEDS")     # M6 7.2 — 입수 레벨 문턱(누적)
GACHA_LV_MAX = int(num("GACHA_LV_MAX"))
assert len(GACHA_XP_NEEDS) == GACHA_LV_MAX, (len(GACHA_XP_NEEDS), GACHA_LV_MAX)   # M6 7.2 — 문턱 수 = 단계 수
GACHA_COST_PLANS = int(num("GACHA_COST_PLANS"))   # M6 7.1 — 장비 1개 = 설계도 1개
STAGE_PLANS = int(num("STAGE_PLANS"))
BOSS_PLANS = int(num("BOSS_PLANS"))
RECLEAR_PLANS = int(num("RECLEAR_PLANS"))       # 다시 깨는 단계
LEGACY_BP_RATIO = num("LEGACY_BP_RATIO")            # v5 저장본 이전에만
LEGACY_GACHA_COST_FRAC = num("LEGACY_GACHA_COST_FRAC")
ZONE_COUNT = int(num("ZONE_COUNT"))
TIER_MAX = int(num("TIER_MAX"))
MAX_ONSCREEN_ZOMBIES = int(num("MAX_ONSCREEN_ZOMBIES"))
ZONE_HP0, ZONE_HP_G = num("ZONE_HP0"), num("ZONE_HP_G")
ZONE_RW0, ZONE_RW_G = num("ZONE_RW0"), num("ZONE_RW_G")
WALL_EVERY, WALL_KILL_MULT, WALL_START = int(num("WALL_EVERY")), int(num("WALL_KILL_MULT")), int(num("WALL_START"))   # M2 벽 (처치 수, 구역 10 부터) · M14 ×1
FARM_GAIN, FARM_MAX_SEC = num("FARM_GAIN"), num("FARM_MAX_SEC")   # M14 — 보강
WALL_HP_MULT = num("WALL_HP_MULT")   # M15 1 — 벽 체력
HP_KNOTS = matrix("HP_KNOTS")        # M15 1 — 구역별 체력 매듭
ZOMBIE_DPS_RATIO = num("ZOMBIE_DPS_RATIO")
STAGES_PER_ZONE = int(num("STAGES_PER_ZONE"))
STAGE_BONUS_RATIO = num("STAGE_BONUS_RATIO")
TIER_MAX_PORT = int(num("TIER_MAX"))
GEAR_SHAPES = int(num("GEAR_SHAPES"))
GEAR_AFFIXES = int(num("GEAR_AFFIXES"))
GEAR_SLOT_IDS = ["weapon", "head", "body", "hands", "feet"]
# M10 (지시 #155) — 장비 융합 사다리. 무작위 옵션(AFFIX_DEFS)·판매(SELL_PRICE_FRAC)는 없어졌다. 값은 전부 원본에서 읽는다.
GEAR_STEPS = int(num("GEAR_STEPS"))
assert re.search(r"LADDER = 8 \* GEAR_STEPS", SRC), "원본 LADDER 식이 바뀌었다 — 여기도 맞춘다"
LADDER = 8 * GEAR_STEPS
FUSE_N = int(num("FUSE_N"))
WEAPON_POW_G = num("WEAPON_POW_G")
OWN_PER_TIER = num("OWN_PER_TIER")
def _dict(name):
    m = re.search(r"const\s+" + name + r"\s*=\s*\{([^}]*)\}", SRC)
    if not m:
        raise ValueError("game/index.html 에서 표 %s 를 못 찾았다" % name)
    return {k: (v[1:-1] if v[0] == "'" else float(v)) for k, v in re.findall(r"(\w+)\s*:\s*('[^']*'|-?[\d.]+)", m.group(1))}
SLOT_STAT = _dict("SLOT_STAT")
SLOT_EQUIP_G = _dict("SLOT_EQUIP_G")
REBIRTH_MIN_ZONE = int(num("REBIRTH_MIN_ZONE"))
MEDAL_PER = num("MEDAL_PER")
SKILLS = table("SKILLS")                   # M12 (지시 #160) — 스킬 8개
SKILL_IDS = [d["id"] for d in SKILLS]
SKILL_SLOTS = int(num("SKILL_SLOTS")); SKILL_LV_MAX = int(num("SKILL_LV_MAX")); SKILL_LV_STEP = num("SKILL_LV_STEP"); SKILL_POW = num("SKILL_POW")
BOSS_BOOKS_FIRST = int(num("BOSS_BOOKS_FIRST")); BOSS_BOOKS_AGAIN = int(num("BOSS_BOOKS_AGAIN")); ZONE_BOOKS = int(num("ZONE_BOOKS"))
SKILL_STRIP_H = num("SKILL_STRIP_H")
STAGE_WALK_SEC = num("STAGE_WALK_SEC"); ZONE_TRAVEL_SEC = num("ZONE_TRAVEL_SEC")   # M13 (지시 #161) — 걷기·구역 이동 대기
LOOP_G = num("LOOP_G")                     # M11 1 — 회차 배수(좀비)
LOOP_RW = num("LOOP_RW")                   # M11 1 — 회차 배수(처치 보상)
KEY_MAX = int(num("KEY_MAX"))
SUPPLY_SHARE = num("SUPPLY_SHARE")
LOGIN_DAYS = int(num("LOGIN_DAYS"))
DAY_MS = int(num("DAY_MS"))
LOGIN_SHARES = [float(x) for x in re.search(
    r"const\s+LOGIN_SHARES\s*=\s*\[([^\]]*)\]", SRC).group(1).replace(" ", "").split(",") if x]
DAILY_BUDGET = num("DAILY_BUDGET")
KILLS_PER_ZONE = int(num("KILLS_PER_ZONE"))
BOSS_EVERY = int(num("BOSS_EVERY"))
BOSS_HP_MULT = num("BOSS_HP_MULT")
BOSS_CHARGE_EVERY = num("BOSS_CHARGE_EVERY")
BOSS_CHARGE_TIME = num("BOSS_CHARGE_TIME")
BOSS_CHARGE_MULT = num("BOSS_CHARGE_MULT")
TIER_COST_MULT = num("TIER_COST_MULT")
TIER_POWER_MULT = num("TIER_POWER_MULT")     # M6 재설계 — 등급 위력 곱하기
OFFLINE_MAX_HOURS = num("OFFLINE_MAX_HOURS")
OFFLINE_RATE = num("OFFLINE_RATE")
MEDAL_PERKS = table("MEDAL_PERKS")   # M27 (지시 #192) — 훈장 상점. 원본 표에서 읽는다
CAMP_BUILDS = table("CAMP_BUILDS")   # M28 (지시 #193) — 남쪽 캠프
MATS_BOSS = int(num("MATS_BOSS")); MATS_ZONE = int(num("MATS_ZONE")); AD_CAMP_MIN = int(num("AD_CAMP_MIN"))
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
EQUIP_STRIP_H = num("EQUIP_STRIP_H")     # M5 2.4 — 장비 탭 장착 띠
MIN_TAP_CSS = num("MIN_TAP_CSS")

STATS = table("STATS")
WEAPON_TYPES = table("WEAPON_TYPES")
# M4 4.3 (a) 2026-09-17 — 장비로만 오르는 축. **원본의 gearOnly 에서 읽는다.** 여기 손으로 적으면
# 원본과 갈라진다 (사례 23: 한 개념이 두 곳에 있으면 한 곳은 남는다).
GEAR_ONLY_STATS = {s["id"] for s in STATS if s.get("gearOnly")}
# 지시 #187 — 퀘스트 셋(일일 고정 5 · 일일 완료 · 반복 · 업적). 원본 표에서 읽는다(손으로 베끼지 않는다).
QUEST_DAILY = table("QUEST_DAILY")
QUEST_DAILY_ALL = table("QUEST_DAILY_ALL")
QUEST_REPEAT = table("QUEST_REPEAT")
QUEST_ACH = table("QUEST_ACH")
QUEST_DAILY_SHARE = num("QUEST_DAILY_SHARE")
QUEST_CUM = tuple(re.findall(r"'(\w+)'", re.search(r"const\s+QUEST_CUM\s*=\s*\[([^\]]*)\]", SRC).group(1)))
STORY_ZONES = [int(x) for x in re.search(r"const STORY_ZONES = \[([^\]]*)\]", SRC).group(1).split(",")]   # 지시 #188
QUEST_DEFS_IDS = [q["id"] for q in QUEST_DAILY]                 # 도구 호환 — 일일 id
QUEST_NEEDS = {q["id"]: int(q["need"]) for q in QUEST_DAILY}


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
    "acceptRevive": "22975d87d579a771",
    "adRowY": "5ed5d78e1b23b919",
    "applyDamage": "44f3fc0acd0ea484",
    "applyOffline": "2830611cc9c8775f",
    "attacksPerSec": "0639c7d834dcbe23",
    "bestOwned": "07d4ef38def7b50f",
    "boostActive": "ed9a9a513325e7ef",
    "buildButtons": "99cc5b010d9fa455",
    "buyPerk": "936716819438d513",
    "buyStat": "e92f891d410963f4",
    "campBuild": "106561b9c0bf0d6a",
    "campTick": "1a705e07a9ddba77",
    "canEquipBetter": "66a45cfc3ca1b1d8",
    "canFuse": "236dc9baad626747",
    "canRebirth": "a66b83d63aeb50bb",
    "castSkill": "fc1f134eca259221",
    "curGachaLv": "e40d82faf896292f",
    "curWeapon": "837d285bf3118179",
    "dailyBudget": "51f1b98162132ed0",
    "damageZombie": "de858f78fa27b6f3",
    "dayIndex": "e395fb011be7dfbc",
    "doRebirth": "81a07c381c87f951",
    "equipBest": "0f92c8c2f2743745",
    "firstClear": "469a179f675bd42f",
    "fitGame": "efc52009e8769fc5",
    "freshSkills": "d57168837a130519",
    "freshState": "a74240a5444abea9",
    "fuseAll": "82b2582d09c7805e",
    "gachaCost": "b5e4af366ce8db89",
    "gachaLevel": "17ab77ebf0a0fe9d",
    "gachaRoll": "c0bb58367ea73ed8",
    "gainGear": "506e3715d9741927",
    "gearItem": "8e278c2d1e03be09",
    "gearMult": "42c8e66405ac5b6f",
    "gearScore": "2d4b4f6590669ec3",
    "hitButton": "8564f49dbd9cc319",
    "hitDamage": "86e5dbdf14ea5395",
    "hpKnot": "33a629695dd9f1af",
    "hurtZombie": "5deea434c00ebeef",
    "idxOf": "eef263846326e9ec",
    "isBossKill": "e461a4a51bbb69c5",
    "isWallZone": "6f63f1e3b34209a7",
    "killReward": "0ef3ffe5d2eb73ba",
    "killZombie": "818c5e00130cf3df",
    "layout": "a6a07a236eb89472",
    "listBotY": "58cb9bb82a45c13d",
    "listTopY": "85ee3342407d5876",
    "loopMult": "72fea6b1ab010c6d",
    "loopRwMult": "d559223a9b92f280",
    "maxHP": "85e54826f897f7c7",
    "medalMult": "d4986f2c59b416d2",
    "medalsFor": "40a1cb07ee003bd6",
    "migrate": "a92bac796c93ec8c",
    "onDeath": "bd9a06f0be2dbe37",
    "openSupply": "ef504f009bbf894e",
    "partsPerSecondEstimate": "424babe8c5fc62f9",
    "pierceShot": "9db3268bc8df46f8",
    "playerDPS": "06d866ae2129b84d",
    "pullGacha": "851dba3af0fc6fb0",
    "questReady": "3994e1c48868d364",
    "regenPerSec": "73badd17c9fc2857",
    "rewardMult": "bff5bcb3e94a3395",
    "rollGear": "d5a4ca6ac6f36122",
    "rollTier": "802162caae06b933",
    "rollTierOdds": "ed4822ee0404a536",
    "rolloverDay": "5da47dfc82599be4",
    "skillHit": "2328493bec595a31",
    "skillLvMult": "8a2e2daddc0980dc",
    "skillSpdMult": "5b142d6cdf65193e",
    "skillToggle": "b0d0a29dc3a841e4",
    "skillUp": "af35c3971eed7be5",
    "skillUpCost": "f6bfc45233684273",
    "spawnZombie": "d4054c63f48a4d4a",
    "stageKills": "4cb2b09008d21635",
    "statCost": "3915c9b212b37571",
    "statDef": "e7ad6087978fd6ec",
    "statOf": "64433344a9e069b6",
    "stepCombat": "77da0715ffc39789",
    "stepSkills": "e73576e1cfdf7432",
    "tabRowY": "d001ac81a8afa161",
    "takeQuest": "49f5bdc1529732f0",
    "unlockSkills": "d2185638165f6aeb",
    "weaponOf": "cd23351858d3c448",
    "weaponPower": "8fcbdfc907029bf9",
    "zoneDPS": "9abab3ae0b004352",
    "zoneHP": "bdeda52960435a6b",
    "zoneReward": "fc08ad169107745f",
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
        self.skillRt = dict(cd={}, act={}, pierce=0, turretAcc=0.0, fireAcc=0.0, fireT=0.0, tT=0.0)   # M12 — 발동 상태(저장 안 함)
        self.skillPopup = None
        self.moveT = 0.0                 # M13 — 걷기·구역 이동 남은 시간(저장 안 함)
        self.farm = None                 # M14 — 보강
        self.dmgShot = 0.0; self.dmgSkill = 0.0   # 포트에만 있는 계수기 — 스킬 피해 몫(tools/skill_share.py)

    # ---- 저장 ----
    def freshState(self):
        return dict(v=SAVE_VERSION, parts=0.0, plans=0.0, zone=1, kills=0,
                    gear=dict(weapon=0), inv=self.emptyInv(), own=dict(self.emptyInv(), weapon=[1] + [0] * (LADDER - 1)), fresh={},   # M10
                    medals=0, rebirths=0, loop=1, medalSpent=0, perk={},   # M27 — 훈장 상점
                    mats=0, camp=dict(lv={}, build=None),   # M28 — 자재 · 캠프
                    skills=self.freshSkills(), books=0, peakZone=1,   # M12
                    seen={}, rec=dict(loop=1, sec=0.0, zone=1, sec60=None, list=[]),   # M15 — 재화 안내 · 회차 기록
                    day=0, maxDay=0, story=dict(seen={}, tut=0), qd={}, qdTaken={}, qr={}, qrLv={}, qc={}, qa={},   # 지시 #187 — 퀘스트 · #188 줄거리
                    login=dict(streak=0, lastDay=-1), keys=KEY_MAX,
                    lv=dict(atk=0, spd=0, hp=0, reg=0, inc=0),
                    hp=100.0, bestZone=1, totalKills=0, gachaXp=0, clearBest=0,   # M6 7.2 · 7.1
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
        if raw.get("v") == 4:                 # M6 2.3: 무기가 장비가 됐다 (원본 migrate 와 같은 구조)
            owned = raw.get("owned") or {"pipe": 1}; cur = raw.get("weapon") or "pipe"
            gear = dict(raw.get("gear") or {}); bag = list(raw.get("bag") or [])
            if not gear.get("weapon"):
                gear["weapon"] = dict(slot="weapon", type=cur, tier=owned.get(cur, 1), affixes=[], zone=raw.get("bestZone") or 1)
            for wid, tr in owned.items():
                if wid != cur and tr > 0 and wid in ("pipe", "rifle", "shotgun", "flamer", "crossbow", "mine", "mg", "launcher", "saw", "rail"):   # M10: 옛 무기 id
                    bag.append(dict(slot="weapon", type=wid, tier=tr, affixes=[], zone=raw.get("bestZone") or 1))
            raw = dict(raw, v=5, gear=gear, bag=bag, gachaLv=0)
            raw.pop("owned", None); raw.pop("weapon", None)
        if raw.get("v") == 5:                 # M6 7: 설계도 돈 → 개수, 강화 단계 → 입수 경험치 (원본 migrate 와 같은 구조)
            inc_s = next(s for s in STATS if s["id"] == "inc"); inc_lv = (raw.get("lv") or {}).get("inc", 0)
            legacy_one = self.zoneIncome(raw.get("bestZone") or 1) * LEGACY_BP_RATIO * LEGACY_GACHA_COST_FRAC * inc_s["base"] * (inc_s["growth"] ** inc_lv)
            cnt = min(50, math.floor((raw.get("plans") or 0.0) / max(1.0, legacy_one)))
            lv_old = max(0, min(GACHA_LV_MAX, raw.get("gachaLv") or 0))
            raw = dict(raw, v=6, plans=cnt, gachaXp=(GACHA_XP_NEEDS[lv_old - 1] if lv_old > 0 else 0), clearBest=(raw.get("bestZone") or 1) * STAGES_PER_ZONE)
            raw.pop("gachaLv", None)
        if raw.get("v") == 6:                 # M10: 낀 장비·가방 → 사다리 칸 개수 (원본 migrate 와 같은 구조)
            old_mult = dict(pipe=1.0, rifle=1.45, shotgun=1.9, flamer=2.6, crossbow=3.4, mine=4.5, mg=6.0, launcher=8.0, saw=10.5, rail=14.0)
            def to_idx(g):
                if not isinstance(g, dict):
                    return None
                if g.get("slot") == "weapon":
                    p = old_mult.get(g.get("type"), 1.0) * (1.5 ** ((g.get("tier") or 1) - 1))
                    return max(0, min(LADDER - 1, jsround(math.log(p) / math.log(WEAPON_POW_G))))
                return self.idxOf(max(1, min(TIER_MAX_PORT, g.get("tier") or 1)), 3)
            inv, own, gear = self.emptyInv(), self.emptyInv(), {}
            for g in list((raw.get("gear") or {}).values()) + list(raw.get("bag") or []):
                k = to_idx(g)
                if k is None or g.get("slot") not in inv:
                    continue
                inv[g["slot"]][k] += 1; own[g["slot"]][k] = 1
            for sl, g in (raw.get("gear") or {}).items():
                k = to_idx(g)
                if k is not None and sl in own:
                    gear[sl] = k; inv[sl][k] = max(0, inv[sl][k] - 1)
            if gear.get("weapon") is None:
                gear["weapon"] = 0; own["weapon"][0] = 1
            raw = dict(raw, v=7, gear=gear, inv=inv, own=own, fresh={}, medals=0, rebirths=0)
            raw.pop("bag", None)
        if raw.get("v") == 7:                 # M11: 회차 = 환생 수 + 1
            raw = dict(raw, v=8, loop=(raw.get("rebirths") or 0) + 1)
        if raw.get("v") == 8:                 # M12: 간 깊이까지 해금, 앞 칸부터
            pk = max(1, raw.get("bestZone") or 1, raw.get("zone") or 1); sk = self.freshSkills()
            for d in SKILLS:
                if pk > d["unlock"] and not sk["lv"][d["id"]]:
                    sk["lv"][d["id"]] = 1
                    if None in sk["slots"]:
                        sk["slots"][sk["slots"].index(None)] = d["id"]
            raw = dict(raw, v=9, skills=sk, books=0, peakZone=pk)
        if raw.get("v") == 9:                 # M15: 가진 재화는 안내를 본 것으로, 기록은 지금 회차부터
            sn = dict(parts=1, plans=1 if (raw.get("plans") or 0) > 0 or (raw.get("gachaXp") or 0) > 0 else 0,
                      books=1 if (raw.get("books") or 0) > 0 or (raw.get("peakZone") or 1) > 5 else 0, medals=1 if (raw.get("medals") or 0) > 0 else 0)
            raw = dict(raw, v=10, seen=sn, rec=dict(loop=raw.get("loop") or 1, sec=0.0, zone=max(1, raw.get("bestZone") or 1), sec60=None, list=[]))
        if raw.get("v") != SAVE_VERSION:
            return self.freshState()
        s = self.freshState()
        for k in list(s.keys()):
            if k in raw:
                s[k] = raw[k]
        if not isinstance((s.get("gear") or {}).get("weapon"), (int, float)):
            s["gear"] = dict(s.get("gear") or {}, weapon=0)
        for sl in GEAR_SLOT_IDS:   # M10 — 칸 배열 길이를 맞춘다
            s["inv"][sl] = [max(0, int(((s.get("inv") or {}).get(sl) or [])[k] if k < len(((s.get("inv") or {}).get(sl) or [])) else 0)) for k in range(LADDER)]
            s["own"][sl] = [1 if (k < len(((s.get("own") or {}).get(sl) or [])) and ((s.get("own") or {}).get(sl) or [])[k]) else 0 for k in range(LADDER)]
        s["own"]["weapon"][int(s["gear"]["weapon"])] = 1
        sk = s.get("skills") if isinstance(s.get("skills"), dict) else {}   # M12 — 스킬 칸 모양을 맞춘다
        lvs = {d["id"]: max(0, min(SKILL_LV_MAX, int((sk.get("lv") or {}).get(d["id"]) or 0))) for d in SKILLS}
        lvs["focus"] = max(1, lvs["focus"]); slots = []
        for i in range(SKILL_SLOTS):
            sid = (sk.get("slots") or [None] * SKILL_SLOTS)[i] if i < len(sk.get("slots") or []) else None
            slots.append(sid if sid and lvs.get(sid, 0) > 0 and sid not in slots else None)
        s["skills"] = dict(lv=lvs, slots=slots)
        s["books"] = max(0, int(s.get("books") or 0)); s["peakZone"] = max(1, s.get("peakZone") or 1, s.get("bestZone") or 1)
        for k in ("qd", "qdTaken", "qr", "qrLv", "qc", "qa"):   # 지시 #187 — 퀘스트 칸 모양 · 처음이면 누계를 지금 상태로
            if not isinstance(s.get(k), dict):
                s[k] = {}
        if "qc" not in raw:
            s["qc"] = {"stat": sum((raw.get("lv") or {}).values()), "skillup": sum(max(0, (s["skills"]["lv"].get(d["id"]) or 0) - 1) for d in SKILLS)}
        pk = s.get("perk") if isinstance(s.get("perk"), dict) else {}   # M27 — 훈장 상점 칸 모양
        s["perk"] = {d["id"]: max(0, min(int(d["max"]), int(pk.get(d["id"]) or 0))) for d in MEDAL_PERKS}
        s["medalSpent"] = max(0, min(s.get("medals") or 0, int(s.get("medalSpent") or 0)))
        cp = s.get("camp") if isinstance(s.get("camp"), dict) else {}   # M28 — 캠프 칸 모양
        lv0 = cp.get("lv") if isinstance(cp.get("lv"), dict) else {}
        bd = cp.get("build")
        ok = isinstance(bd, dict) and any(d["id"] == bd.get("id") for d in CAMP_BUILDS) and isinstance(bd.get("until"), (int, float))
        s["camp"] = dict(lv={d["id"]: max(0, min(int(d["max"]), int(lv0.get(d["id"]) or 0))) for d in CAMP_BUILDS},
                         build=dict(id=bd["id"], until=bd["until"]) if ok else None)
        s["mats"] = max(0, int(s.get("mats") or 0))
        st = s.get("story") if isinstance(s.get("story"), dict) else {}   # 지시 #188 — 줄거리 칸 · 하던 사람은 튜토리얼 건너뜀
        s["story"] = {"seen": st.get("seen") if isinstance(st.get("seen"), dict) else {}, "tut": max(0, min(4, int(st.get("tut") or 0)))}
        if "story" not in raw and ((raw.get("totalKills") or 0) > 30 or s["peakZone"] > 1):
            s["story"]["tut"] = 4; s["story"]["seen"]["intro"] = 1
            for z in STORY_ZONES:
                if s["peakZone"] >= z:
                    s["story"]["seen"]["zone%d" % z] = 1
            if (s.get("loop") or 1) >= 2:
                s["story"]["seen"]["loop2"] = 1
        r = s.get("rec") if isinstance(s.get("rec"), dict) else {}   # M15 — 기록·안내 모양을 맞춘다
        s60 = r.get("sec60")
        s["rec"] = dict(loop=max(1, int(r.get("loop") or s.get("loop") or 1)), sec=max(0.0, float(r.get("sec") or 0)), zone=max(1, int(r.get("zone") or 1)),
                        sec60=(float(s60) if isinstance(s60, (int, float)) and s60 >= 0 else None),
                        list=[e for e in (r.get("list") if isinstance(r.get("list"), list) else []) if isinstance(e, dict) and (e.get("l") or 0) >= 1][-20:])
        if not isinstance(s.get("seen"), dict):
            s["seen"] = {}
        # 옛 저장본에는 inc 가 없다. 0 으로 채운다 (원본과 같다)
        lv = dict(atk=0, spd=0, hp=0, reg=0, inc=0)
        lv.update(raw.get("lv") or {})
        s["lv"] = lv
        return s

    # ---- 파생 ----
    def statDef(self, i):
        return next(s for s in STATS if s["id"] == i)

    def statOf(self, i):
        s = self.statDef(i); lv = self.G["lv"].get(i, 0)
        # M6 1.2 — add 면 더하기 성장, cap 은 최종 상한 (원본 statOf 와 같은 구조)
        v = (s["base"] + s["add"] * lv if s.get("add") is not None else s["base"] * (s["growth"] ** lv)) * self.gearMult(i) * self.medalMult(i)   # M10 2
        return min(s["cap"], v) if s.get("cap") is not None else v

    def statCost(self, i):
        s = self.statDef(i)
        return math.ceil(s["cost0"] * (s["costG"] ** self.G["lv"].get(i, 0)))

    def weaponOf(self, i):
        return next(w for w in WEAPON_TYPES if w["id"] == i)

    def curWeapon(self):                      # M10 — 칸 번호에서 묶음으로
        k = (self.G.get("gear") or {}).get("weapon")
        return self.gearItem("weapon", int(k) if isinstance(k, (int, float)) else 0)

    def weaponPower(self):
        return WEAPON_POW_G ** self.curWeapon()["k"]   # M10: WEAPON_POW_G^칸

    # ---- M10 사다리 (원본과 같은 식) ----
    @staticmethod
    def emptyInv():
        return {sl: [0] * LADDER for sl in GEAR_SLOT_IDS}

    @staticmethod
    def idxOf(tier, step):
        return (tier - 1) * GEAR_STEPS + (GEAR_STEPS - step)

    @staticmethod
    def idxTier(k):
        return k // GEAR_STEPS + 1

    @staticmethod
    def gearItem(slot, k):
        it = dict(slot=slot, k=k, tier=k // GEAR_STEPS + 1, step=GEAR_STEPS - (k % GEAR_STEPS))
        if slot == "weapon":
            it["type"] = WEAPON_TYPES[min(len(WEAPON_TYPES) - 1, (k * len(WEAPON_TYPES)) // LADDER)]["id"]
        else:
            it["shape"] = min(GEAR_SHAPES - 1, (k * GEAR_SHAPES) // LADDER)
        return it

    def gainGear(self, g):
        is_new = not self.G["own"][g["slot"]][g["k"]]
        self.G["inv"][g["slot"]][g["k"]] += 1; self.G["own"][g["slot"]][g["k"]] = 1
        if is_new:
            self.G.setdefault("fresh", {})[g["slot"]] = True
        return is_new

    def fuseAll(self):
        made = 0
        for sl in GEAR_SLOT_IDS:
            inv = self.G["inv"][sl]
            for k in range(LADDER - 1):
                q = inv[k] // FUSE_N
                if not q:
                    continue
                inv[k] -= q * FUSE_N; inv[k + 1] += q; made += q
                if not self.G["own"][sl][k + 1]:
                    self.G["own"][sl][k + 1] = 1; self.G.setdefault("fresh", {})[sl] = True
        if made:
            self.questProgress("fuse", made)
        return made

    def bestOwned(self, sl):
        own = self.G["own"][sl]
        for k in range(LADDER - 1, -1, -1):
            if own[k]:
                return k
        return -1

    def equipBest(self):
        n = 0
        for sl in GEAR_SLOT_IDS:
            k = self.bestOwned(sl)
            if k >= 0 and self.G["gear"].get(sl) != k:
                self.G["gear"][sl] = k; n += 1
        if n:
            self.questProgress("equip", n)
        return n

    def canFuse(self):
        return any(self.G["inv"][sl][k] >= FUSE_N for sl in GEAR_SLOT_IDS for k in range(LADDER - 1))

    def canEquipBetter(self):
        return any(self.bestOwned(sl) >= 0 and (not isinstance(self.G["gear"].get(sl), (int, float)) or self.bestOwned(sl) > self.G["gear"][sl]) for sl in GEAR_SLOT_IDS)

    # ---- M10 2 환생 ----
    def loopMult(self):
        return LOOP_G ** (max(1, (self.G.get("loop") or 1) if getattr(self, "G", None) else 1) - 1)   # M11 1

    def loopRwMult(self):
        return LOOP_RW ** (max(1, (self.G.get("loop") or 1) if getattr(self, "G", None) else 1) - 1)   # M11 1

    def medalsFor(self, bz):
        return math.floor((bz - (REBIRTH_MIN_ZONE - 1)) ** 1.5) * max(1, self.G.get("loop") or 1) if bz >= REBIRTH_MIN_ZONE else 0   # M11: × 회차

    def medalMult(self, sid):
        m = 1 + MEDAL_PER * (self.G.get("medals") or 0) if sid in ("atk", "inc") else 1.0
        for d in MEDAL_PERKS:   # M27 — 상점 능력치
            if d.get("stat") == sid:
                m *= 1 + d["per"] * self.perkLv(d["id"])
        for d in CAMP_BUILDS:   # M28 캠프
            if d.get("stat") == sid:
                m *= 1 + d["per"] * self.campLv(d["id"])
        return m

    # ---- M28 남쪽 캠프 (원본과 같은 구조) ----
    def campDef(self, cid):
        return next(d for d in CAMP_BUILDS if d["id"] == cid)

    def campLv(self, cid):
        return ((self.G.get("camp") or {}).get("lv") or {}).get(cid, 0)

    def campCost(self, cid):
        d = self.campDef(cid)
        return math.ceil(d["cost0"] * d["costG"] ** self.campLv(cid))

    def campTime(self, cid):
        d = self.campDef(cid)
        return round(d["t0"] * d["tG"] ** self.campLv(cid))

    def campEff(self, key):
        return sum(d[key] * self.campLv(d["id"]) for d in CAMP_BUILDS if d.get(key))

    def campMats(self, n):
        g = math.floor(n * (1 + self.campEff("mats")))
        self.G["mats"] = (self.G.get("mats") or 0) + g
        return g

    def campBuild(self, cid, now):
        d = next((x for x in CAMP_BUILDS if x["id"] == cid), None)
        if d is None or self.G["camp"]["build"] or self.campLv(cid) >= d["max"]:
            return False
        c = self.campCost(cid)
        if (self.G.get("mats") or 0) < c:
            return False
        self.G["mats"] -= c
        self.G["camp"]["build"] = dict(id=cid, until=now + self.campTime(cid) * 1000)
        return True

    def campTick(self, now):
        b = (self.G.get("camp") or {}).get("build")
        if not b or now < b["until"]:
            return None
        self.G["camp"]["lv"][b["id"]] = self.campLv(b["id"]) + 1
        self.G["camp"]["build"] = None
        return b["id"]

    def campAuto(self):
        """포트에만 — 쉬고 있으면 지을 수 있는 것 중 값이 가장 싼 것을 바로 짓는다(auto_run(camp=True) 에서만)."""
        if self.G["camp"]["build"]:
            return
        c = [(self.campCost(d["id"]), d["id"]) for d in CAMP_BUILDS if self.campLv(d["id"]) < d["max"]]
        c = [x for x in c if x[0] <= (self.G.get("mats") or 0)]
        if c:
            self.campBuild(min(c)[1], self.now_ms)

    # ---- M27 훈장 상점 (원본과 같은 구조) ----
    def perkLv(self, pid):
        return (self.G.get("perk") or {}).get(pid, 0)

    def perkCost(self, pid):
        d = next(x for x in MEDAL_PERKS if x["id"] == pid)
        return math.ceil(d["cost0"] * d["costG"] ** self.perkLv(pid))

    def medalsFree(self):
        return max(0, (self.G.get("medals") or 0) - (self.G.get("medalSpent") or 0))

    def buyPerk(self, pid):
        d = next((x for x in MEDAL_PERKS if x["id"] == pid), None)
        if d is None or self.perkLv(pid) >= d["max"]:
            return False
        c = self.perkCost(pid)
        if self.medalsFree() < c:
            return False
        self.G["medalSpent"] = (self.G.get("medalSpent") or 0) + c
        self.G.setdefault("perk", {})[pid] = self.perkLv(pid) + 1
        return True

    def offlineMaxHours(self):
        return OFFLINE_MAX_HOURS + self.perkLv("night")

    def canRebirth(self):
        return (self.G.get("bestZone") or 1) >= REBIRTH_MIN_ZONE

    def doRebirth(self):
        if not self.canRebirth():
            return 0
        gain = self.medalsFor(self.G.get("bestZone") or 1)
        self.G["medals"] = (self.G.get("medals") or 0) + gain; self.G["rebirths"] = (self.G.get("rebirths") or 0) + 1
        self.G["loop"] = (self.G.get("loop") or 1) + 1   # M11 1
        z0 = min(ZONE_COUNT, 1 + self.perkLv("start"))   # M27 선발대
        self.G.update(zone=z0, bestZone=z0, kills=0, parts=0.0, clearBest=0)
        for k in list(self.G["lv"].keys()):
            self.G["lv"][k] = 0
        self.G["hp"] = self.maxHP()
        self.killIndex = 0; self.zombies = []; self.reviveOffer = None
        self.skillRt = dict(cd={}, act={}, pierce=0, turretAcc=0.0, fireAcc=0.0, fireT=0.0, tT=0.0)   # M12
        self.moveT = 0.0                                   # M13
        self.farm = None                                   # M14
        return gain

    def hitDamage(self):
        # M6 1.2 — 원본은 한 발마다 굴린다(hitDamage). 자는 **기대값**(원본 expectedHit)으로 잰다 — 정본 '치명타' 행.
        p = min(1.0, self.statOf("crit"))
        return self.statOf("atk") * self.weaponPower() * (1 + p * (self.statOf("cdmg") - 1))

    def attacksPerSec(self):
        return self.statOf("spd") * self.skillSpdMult()   # M12: 집중 사격·아드레날린(자동 스킬). M4 의 탭 집중 사격은 없어졌다

    # ---- M12 스킬 (원본과 같은 구조) ----
    @staticmethod
    def freshSkills():
        lv = {d["id"]: 0 for d in SKILLS}; lv["focus"] = 1
        return dict(lv=lv, slots=["focus"] + [None] * (SKILL_SLOTS - 1))

    @staticmethod
    def skillDef(sid):
        return next((d for d in SKILLS if d["id"] == sid), None)

    def skillLv(self, sid):
        return ((self.G.get("skills") or {}).get("lv") or {}).get(sid) or 0

    def skillLvMult(self, sid):
        return SKILL_POW * (1 + SKILL_LV_STEP * (max(1, self.skillLv(sid)) - 1))

    def skillUpCost(self, sid):
        return max(1, -(-self.skillLv(sid) // 2))   # M14 2.1 — ⌈L/2⌉

    def skillHit(self):
        return self.playerDPS() * (1 + self.campEff("skill"))   # M12 3.2 — 1초 피해 단위 · M28 작업장

    def skillActive(self, sid):
        return (self.skillRt["act"].get(sid) or 0) > 0

    def skillSpdMult(self):
        m = 1.0
        if self.skillActive("focus"):
            m *= 1 + self.skillDef("focus")["pow"] * self.skillLvMult("focus")
        if self.skillActive("adren"):
            m *= 1 + self.skillDef("adren")["pow"] * self.skillLvMult("adren")
        return m

    def unlockSkills(self):
        for d in SKILLS:
            if (self.G.get("peakZone") or 1) > d["unlock"] and not self.skillLv(d["id"]):
                self.G["skills"]["lv"][d["id"]] = 1
                sl = self.G["skills"]["slots"]
                if None in sl:
                    sl[sl.index(None)] = d["id"]

    def skillUp(self, sid):
        c = self.skillUpCost(sid)
        if not self.skillLv(sid) or self.skillLv(sid) >= SKILL_LV_MAX or (self.G.get("books") or 0) < c:
            return False
        self.G["books"] -= c; self.G["skills"]["lv"][sid] += 1
        self.questProgress("skillup", 1)   # 지시 #187
        return True

    def skillToggle(self, sid):
        sl = self.G["skills"]["slots"]
        if sid in sl:
            sl[sl.index(sid)] = None; return True
        if not self.skillLv(sid) or None not in sl:
            return False
        sl[sl.index(None)] = sid; self.skillRt["cd"][sid] = max(self.skillRt["cd"].get(sid) or 0, 0)
        return True

    def hurtZombie(self, z, dmg, show=False):
        self.dmgSkill += min(dmg, max(0.0, z["hp"]))   # 계수기(원본에 없다)
        z["hp"] -= dmg
        if z["hp"] <= 0:
            self.killZombie(z)

    def castSkill(self, d):
        lm = self.skillLvMult(d["id"])
        if d["id"] == "grenade":
            for z in sorted(self.zombies, key=lambda z: z["x"])[:int(d["n"])]:
                self.hurtZombie(z, self.skillHit() * d["pow"] * lm, True)
        elif d["id"] == "aid":
            self.G["hp"] = min(self.maxHP(), self.G["hp"] + self.maxHP() * d["pow"] * lm)
        elif d["id"] == "strike":
            for z in list(self.zombies):
                self.hurtZombie(z, self.skillHit() * d["pow"] * lm, True)
        if d.get("dur"):
            self.skillRt["act"][d["id"]] = d["dur"]
        self.skillRt["cd"][d["id"]] = d["cd"]
        self.questProgress("skill", 1)

    def stepSkills(self, dt):
        rt = self.skillRt
        for sid in list(rt["act"].keys()):
            rt["act"][sid] = max(0.0, rt["act"][sid] - dt)
        for sid in self.G["skills"]["slots"]:
            if not sid:
                continue
            d = self.skillDef(sid)
            if not d:
                continue
            rt["cd"][sid] = (rt["cd"].get(sid) or 0) - dt
            if rt["cd"][sid] > 0:
                continue
            want = self.G["hp"] < self.maxHP() * 0.7 if sid == "aid" else len(self.zombies) > 0
            if want:
                self.castSkill(d)
            else:
                rt["cd"][sid] = 0
        if self.skillActive("molotov") and self.zombies:
            rt["fireAcc"] += self.skillHit() * self.skillDef("molotov")["pow"] * self.skillLvMult("molotov") * dt; rt["fireT"] += dt
            if rt["fireT"] >= 0.5:
                hit = [z for z in self.zombies if z["x"] <= CONTACT_X + CONTACT_REACH + 0.5]
                for z in list(hit):
                    self.hurtZombie(z, rt["fireAcc"], True)
                rt["fireAcc"] = 0.0; rt["fireT"] = 0.0
        else:
            rt["fireAcc"] = 0.0; rt["fireT"] = 0.0
        if self.skillActive("turret") and self.zombies:
            rt["turretAcc"] += self.playerDPS() * self.skillDef("turret")["pow"] * self.skillLvMult("turret") * dt
            rt["tT"] = rt["tT"] + dt
            if rt["turretAcc"] > 0 and rt["tT"] >= 0.25:
                tg = None
                for z in self.zombies:
                    if tg is None or z["x"] < tg["x"]:
                        tg = z
                if tg is not None:
                    self.shots += 1; self.hurtZombie(tg, rt["turretAcc"], True)
                rt["turretAcc"] = 0.0; rt["tT"] = 0.0
        else:
            rt["turretAcc"] = 0.0; rt["tT"] = 0.0

    def pierceShot(self, dmg):
        if not self.skillActive("pierce") or len(self.zombies) < 2:
            return
        s = sorted(self.zombies, key=lambda z: z["x"])[1]
        self.hurtZombie(s, dmg * self.skillDef("pierce")["pow"] * self.skillLvMult("pierce"), False)

    def playerDPS(self):
        return self.hitDamage() * self.attacksPerSec()

    def maxHP(self):
        return self.statOf("hp")

    def regenPerSec(self):
        return self.statOf("reg")

    def zoneHP(self, z):
        return ZONE_HP0 * (ZONE_HP_G ** (z - 1)) * Sim.hpKnot(z) * (WALL_HP_MULT if Sim.isWallZone(z) else 1) * self.loopMult()   # M11 회차 · M15 휨·벽

    @staticmethod
    def hpKnot(z):
        k = HP_KNOTS
        if z <= k[0][0]:
            return k[0][1]
        for i in range(1, len(k)):
            if z <= k[i][0]:
                f = (z - k[i - 1][0]) / (k[i][0] - k[i - 1][0])
                return math.exp(math.log(k[i - 1][1]) * (1 - f) + math.log(k[i][1]) * f)
        return k[-1][1]

    @staticmethod
    def isWallZone(z):
        return z >= WALL_START and z % WALL_EVERY == 0

    def zoneDPS(self, z):
        return self.zoneHP(z) * ZOMBIE_DPS_RATIO

    @staticmethod
    def stageKills(z):
        return max(1, jsround(Sim.zoneKills(z) / STAGES_PER_ZONE))

    def killReward(self, z):
        return self.zoneReward(z)

    def zoneIncome(self, z):
        return self.zoneReward(z) * Sim.zoneKills(z)

    def rollTier(self, z):
        center = 1 + (TIER_MAX_PORT - 1) * min(1.0, (z - 1) / float(ZONE_COUNT - 1))
        t = jsround(center + (self.rnd() + self.rnd() + self.rnd() - 1.5) * 1.6)
        return max(1, min(TIER_MAX_PORT, t))

    def rollGear(self, z, slot_id=None, tier_given=None):
        # M10 — 부위 무작위 · 등급(영원은 초월로) · 단계 5~1 무작위 → 칸
        slot = slot_id or GEAR_SLOT_IDS[int(self.rnd() * len(GEAR_SLOT_IDS))]
        tier = min(TIER_MAX_PORT - 1, tier_given or self.rollTier(z))
        step = 1 + int(self.rnd() * GEAR_STEPS)
        return self.gearItem(slot, self.idxOf(tier, step))

    @staticmethod
    def gearScore(g):
        return g["k"] if g else -1          # M10 — 칸 번호가 곧 값어치

    def gearMult(self, sid):
        m = 1.0
        for sl in GEAR_SLOT_IDS:
            if SLOT_STAT.get(sl) != sid:
                continue
            k = (self.G.get("gear") or {}).get(sl)
            if sl != "weapon" and isinstance(k, (int, float)):
                m *= SLOT_EQUIP_G[sl] ** (k + 1)
            own = (self.G.get("own") or {}).get(sl) or []
            m *= 1 + OWN_PER_TIER * sum(self.idxTier(i) for i, o in enumerate(own) if o)
        return m

    def _income(self, kind, v):
        """**측정용 계수기.** 원본 게임에는 없다 — 그래서 MIRRORED 대상이 아니다.
           부품이 어디서 들어왔는지 나눠 센다 (M4 4.1 / M4-B3)."""
        d = getattr(self, "income", None)
        if d is None:
            d = self.income = {"kill": 0.0, "sell": 0.0}
        d[kind] = d.get(kind, 0.0) + v

    # ---- M6 2.2 뽑기 ----
    def rollTierOdds(self, lv):
        row = TIER_ODDS[max(0, min(GACHA_LV_MAX, lv or 0))]
        r = self.rnd() * 100
        for i, v in enumerate(row):
            r -= v
            if r < 0:
                return i + 1
        return len(row)

    # ---- M6 7.2 입수 레벨 ----
    @staticmethod
    def gachaLevel(xp):
        lv = 0
        for n in GACHA_XP_NEEDS:
            if (xp or 0) >= n:
                lv += 1
        return min(GACHA_LV_MAX, lv)

    def curGachaLv(self):
        return self.gachaLevel(self.G.get("gachaXp", 0))

    def firstClear(self, idx):                       # M6 7.1
        if idx <= (self.G.get("clearBest") or 0):
            return False
        self.G["clearBest"] = idx
        return True

    def gachaRoll(self):
        return self.rollGear(self.G.get("bestZone") or 1, None, self.rollTierOdds(self.curGachaLv()))

    def gachaCost(self, n):
        return n * GACHA_COST_PLANS                     # M6 7.1

    def pullGacha(self, n):
        # M10 — 뽑은 칸은 개수로 쌓인다(판매·가방·자동 장착 없음). 원본과 같다. 자(auto_run)는 뽑은 뒤 일괄 융합·최고 장착을 누르는 사람이다.
        cost = self.gachaCost(n)
        if self.G.get("plans", 0.0) < cost:
            return False
        self.G["plans"] = self.G.get("plans", 0.0) - cost
        self.G["gachaXp"] = self.G.get("gachaXp", 0) + cost   # M6 7.2
        self.questProgress("pull", n)   # 지시 #151
        items = []
        for _ in range(n):
            g = self.gachaRoll(); items.append({"g": g, "isNew": self.gainGear(g)})
        self.gachaResult = {"mode": "one" if n == 1 else "ten", "items": items}
        return True

    @staticmethod
    def zoneKills(z):
        return KILLS_PER_ZONE * (WALL_KILL_MULT if (z >= WALL_START and z % WALL_EVERY == 0) else 1)   # M2 벽: 구역 10 부터, 처치 수만

    def zoneReward(self, z):
        return ZONE_RW0 * (ZONE_RW_G ** (z - 1)) * KILLS_PER_ZONE / Sim.zoneKills(z) * self.loopRwMult()   # M2 벽: 처치당 보상 ÷3

    @staticmethod
    def isBossKill(z, idx):
        return (z % BOSS_EVERY == 0) and idx == Sim.zoneKills(z) - 1

    def boostActive(self):
        return self.now_ms < (self.G.get("boostUntil") or 0)

    def rewardMult(self):
        return 2 if self.boostActive() else 1

    # ---- 구매 ----
    def questProgress(self, qid, n):
        """지시 #187 — 세 갈래로 센다: 일일(qd) · 반복(qr) · 누계(qc, 업적용). 받기는 claimAll(측정 claim=True 일 때만)."""
        G = self.G
        if any(q["id"] == qid for q in QUEST_DAILY):
            G["qd"][qid] = G["qd"].get(qid, 0) + n
        if any(q["id"] == qid for q in QUEST_REPEAT):
            G["qr"][qid] = G["qr"].get(qid, 0) + n
        if qid in QUEST_CUM:
            G["qc"][qid] = G["qc"].get(qid, 0) + n

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
        # M6 2.1 — 접속 보상은 부품만
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
        self.G["qd"] = {}
        self.G["qdTaken"] = {}   # 지시 #187 — 일일만 리셋
        self.G["keys"] = KEY_MAX
        self.G["day"] = today
        self.G["maxDay"] = today
        w = LOGIN_SHARES[self.G["login"]["streak"] - 1] if self.G["login"]["streak"] - 1 < len(LOGIN_SHARES) else LOGIN_SHARES[0]
        gain = self.grant(self.dailyBudget() * w)
        return {"kind": "login", "day": self.G["login"]["streak"], "gain": gain}

    def achValue(self, aid):
        G = self.G
        return self.curGachaLv() if aid == "gacha" else (G.get("peakZone") or 1) if aid == "zone" else (G.get("rebirths") or 0) if aid == "loop" else (G.get("qc") or {}).get(aid, 0)

    def achTarget(self, a):
        return (self.G["qa"].get(a["id"], 0) + 1) * a["step"]

    def questReady(self, kind, qid=None):
        G = self.G
        if kind == "d":
            q = next((x for x in QUEST_DAILY if x["id"] == qid), None)
            return q is not None and G["qd"].get(qid, 0) >= q["need"] and not G["qdTaken"].get(qid)
        if kind == "da":
            return not G["qdTaken"].get("all") and all(G["qdTaken"].get(q["id"]) for q in QUEST_DAILY)
        if kind == "r":
            q = next((x for x in QUEST_REPEAT if x["id"] == qid), None)
            return q is not None and G["qr"].get(qid, 0) >= q["need"]
        if kind == "a":
            a = next((x for x in QUEST_ACH if x["id"] == qid), None)
            return a is not None and self.achValue(qid) >= self.achTarget(a)
        return False

    def takeQuest(self, kind, qid=None):
        if not self.questReady(kind, qid):
            return False
        G = self.G
        if kind == "d":
            r = next(x for x in QUEST_DAILY if x["id"] == qid); G["qdTaken"][qid] = 1; G["parts"] += self.dailyBudget() * QUEST_DAILY_SHARE
        elif kind == "da":
            r = QUEST_DAILY_ALL[0]; G["qdTaken"]["all"] = 1
        elif kind == "r":
            r = next(x for x in QUEST_REPEAT if x["id"] == qid); G["qr"][qid] -= r["need"]; G["qrLv"][qid] = G["qrLv"].get(qid, 0) + 1
        else:
            r = next(x for x in QUEST_ACH if x["id"] == qid); G["qa"][qid] = G["qa"].get(qid, 0) + 1
        G["plans"] = G.get("plans", 0.0) + int(r.get("plans") or 0)
        G["books"] = (G.get("books") or 0) + int(r.get("books") or 0)
        self.questTaken = getattr(self, "questTaken", 0) + 1
        return True

    def claimAll(self):
        """포트에만 — 받을 수 있는 퀘스트를 전부 받는다(사람이 바로바로 누른다고 치고). auto_run(claim=True) 에서만 부른다."""
        for q in QUEST_DAILY:
            self.takeQuest("d", q["id"])
        self.takeQuest("da")
        for q in QUEST_REPEAT:
            while self.takeQuest("r", q["id"]):
                pass
        for a in QUEST_ACH:
            while self.takeQuest("a", a["id"]):
                pass

    def openSupply(self):
        if (self.G.get("keys") or 0) <= 0:
            return False
        self.G["keys"] -= 1
        return self.grant(self.dailyBudget() * SUPPLY_SHARE / KEY_MAX)

    def buyStat(self, i):
        if i in GEAR_ONLY_STATS:                 # M4 4.3 (M6 1.1 부터 빈 집합)
            return False
        s = self.statDef(i)
        if s.get("cap") is not None and self.statOf(i) >= s["cap"] - 1e-9:   # M6 1.2 상한
            return False
        c = self.statCost(i)
        if self.G["parts"] < c:
            return False
        self.G["parts"] -= c
        self.G["lv"][i] = self.G["lv"].get(i, 0) + 1
        self.questProgress("stat", 1)   # 지시 #151
        return True

    # ---- 버튼 배치 ----
    def tabRowY(self):
        return L["PANEL_TOP"]

    def listTopY(self):
        return L["PANEL_TOP"] + ROW_H + 8 + (EQUIP_STRIP_H + 8 if self.tab == "gear" else SKILL_STRIP_H + 8 if self.tab == "skill" else 0)   # M5 2.4 · M12

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

        if getattr(self, "storyQ", None):        # 지시 #188 — 줄거리 대화(포트 시뮬은 대화를 안 띄운다 — 자리만)
            b("story_next", 0, 0, GAME_W, L["GAME_H"], "scrim")
            return bs
        if self.offlineReport:
            b("scrim", 0, 0, GAME_W, L["GAME_H"], "scrim")
            if not self.offlineReport.get("doubled"):
                b("offline2x", 90, L["GAME_H"] / 2 + 40, 360, ROW_H, "ad")
            b("offline_close", 150, L["GAME_H"] / 2 + 108, 240, ROW_H, "ghost")
            return bs

        # M4 1 — 탭 3개. 폭 164, 간격 8 (원본과 같다)
        if getattr(self, "setPopup", False):     # M20 (지시 #183) · 지시 #184 — 설정 팝업: 틀 · 줄마다 아이콘 켜기/끄기 + 슬라이더 · X
            b("scrim", 0, 0, GAME_W, L["GAME_H"], "scrim")
            px, py, pw = 30, L["GAME_H"] / 2 - 242, GAME_W - 60   # 지시 #198 — 총소리 줄을 더해 434
            b("set_panel", px, py, pw, 434, "hit")
            for i, k in enumerate(("bgm", "sfx", "gun")):
                b("set_" + k + "_on", px + 30, py + 104 + i * 104, 64, 56, "hit")
                b("set_" + k + "_slider", px + 108, py + 104 + i * 104, pw - 138, 56, "hit")
            b("set_close", px + pw - 66, py + 8, 56, 56, "hit")
            b("reset", px + pw / 2 - 120, py + 372, 240, 58, "ghost")   # 지시 #187 — 저장 지우기(테스트)를 퀘스트 팝업에서 여기로
            return bs
        if getattr(self, "campPopup", False):    # M28 — 캠프 팝업: 틀 · 광고 · 시설 6줄 짓기 · X (원본 questPanel·campAdRect·questRewardRect·questCloseRect 와 같은 수)
            b("scrim", 0, 0, GAME_W, L["GAME_H"], "scrim")
            ph = min(L["GAME_H"] - 40, 676); px, py, pw = 20, round((L["GAME_H"] - ph) / 2), GAME_W - 40
            b("camp_panel", px, py, pw, ph, "hit")
            b("camp_ad", px + pw - 14 - 150, py + 63, 150, 58, "hit", bool(self.G["camp"]["build"]))
            for i, d in enumerate(CAMP_BUILDS):
                ok = self.campLv(d["id"]) < d["max"] and not self.G["camp"]["build"] and (self.G.get("mats") or 0) >= self.campCost(d["id"])
                b("camp_build_" + d["id"], px + 14 + (pw - 28) - 108, py + 128 + i * 68 + 3, 100, 58, "hit", ok)
            b("camp_close", px + pw - 64, py + 2, 58, 58, "hit")
            return bs
        if getattr(self, "dailyPopup", False):   # 지시 #187 — 퀘스트 팝업: 틀 · 탭 셋 · 줄마다 보상 버튼 · X (원본 questPanel·questTabRect·questRewardRect·questCloseRect 와 같은 수)
            tab = self.dailyPopup if self.dailyPopup in ("d", "r", "a") else "d"
            b("scrim", 0, 0, GAME_W, L["GAME_H"], "scrim")
            ph = min(L["GAME_H"] - 40, 676); px, py, pw = 20, round((L["GAME_H"] - ph) / 2), GAME_W - 40
            b("quest_panel", px, py, pw, ph, "hit")
            tw = (pw - 28 - 16) / 3
            for i, k in enumerate(("d", "r", "a")):
                b("quest_tab_" + k, px + 14 + i * (tw + 8), py + 60, tw, 58, "on" if tab == k else "off")
            n = (1 + len(QUEST_DAILY) + 1) if tab == "d" else len(QUEST_REPEAT) if tab == "r" else len(QUEST_ACH)   # 일일: 완료 · 5개 · 보급 상자(접속 줄은 버튼 없음)
            for i in range(n):
                b("quest_take", px + 14 + (pw - 28) - 108, py + 128 + i * 68 + 3, 100, 58, "hit")
            b("quest_close", px + pw - 64, py + 2, 58, 58, "hit")
            return bs
        if self.skillPopup:                   # M12 — 스킬 팝업: 끼기/빼기 · 올리기 · 닫기
            sid = self.skillPopup["id"]; on = sid in self.G["skills"]["slots"]; full = None not in self.G["skills"]["slots"]
            b("scrim", 0, 0, GAME_W, L["GAME_H"], "scrim")
            py = L["GAME_H"] / 2 + 20
            b("skill_toggle", 48, py, GAME_W - 96, ROW_H, "ghost" if on else "buy", on or not full)
            b("skill_up", 48, py + ROW_PITCH, GAME_W - 96, ROW_H, "buy", self.skillLv(sid) < SKILL_LV_MAX and (self.G.get("books") or 0) >= self.skillUpCost(sid))
            b("skill_close", 48, py + ROW_PITCH * 2, GAME_W - 96, ROW_H, "ghost")
            return bs
        TW, TG = 118, 6                       # M12: 탭 넷 (540 - 48 - 18) / 4
        for i, tid in enumerate(("stat", "skill", "gear", "rebirth")):   # M12: 능력치·스킬·장비·환생
            b("tab_" + tid, 24 + i * (TW + TG), self.tabRowY(), TW, ROW_H,
              "on" if self.tab == tid else "off")
        if self.tab == "skill":               # M12 — 장착 4칸 띠(누르면 뺀다)
            gap = 8; cw = (GAME_W - 48 - gap * (SKILL_SLOTS - 1)) / SKILL_SLOTS
            for i in range(SKILL_SLOTS):
                b("skill_slot_%d" % i, 24 + i * (cw + gap), self.tabRowY() + ROW_H + 8, cw, SKILL_STRIP_H, "hit", bool(self.G["skills"]["slots"][i]))
        b("camp_btn", GAME_W - 24 - 58 * 3 - 16, L["ARENA_BOT"] - 58 - 8, 58, 58, "mini")   # M28 — 캠프
        b("snd_btn", GAME_W - 24 - 58 - 8 - 58, L["ARENA_BOT"] - 58 - 8, 58, 58, "mini")   # M16 자리 — M20 부터 설정 팝업을 연다
        b("daily_btn", GAME_W - 24 - 58, L["ARENA_BOT"] - 58 - 8, 58, 58, "mini")   # 지시 #151 — 전투 화면 오른쪽 아래

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
            # M5 2.4 — 부위 줄 5개 대신: 합계 · 자동 판매 기준 · 가방 머리 줄. 장착 띠는 버튼이 아니라 여기 없다.
            # 지시 #150 — 장착 띠 칸 5개가 누르는 곳이 됐다(부위 가방). 원본과 같은 자리
            gap = 8; cw = (GAME_W - 48 - gap * 4) / 5
            for i in range(5):
                b("strip_%d" % i, 24 + i * (cw + gap), self.tabRowY() + ROW_H + 8, cw, EQUIP_STRIP_H, "hit")
            put_row("gear_sum", "ghost", False, None)
            for n in (1, 10):                                   # M6 2.2 뽑기 줄
                put_row("gacha_%d" % n, "buy", self.G.get("plans", 0.0) >= self.gachaCost(n), None)
            put_row("fuse_all", "buy", self.canFuse(), None)                 # M10 — 일괄 융합 · 최고 장착
            put_row("equip_best", "buy", self.canEquipBetter(), None)
            put_row("gacha_lv", "ghost", False, None)                    # M6 7.2 — 입수 레벨 줄(정보) · 3.2 확률 보기
            put_row("odds_view", "off", True, None)
            # M6 재설계 — 가방·자동 판매 줄 없음
        elif self.tab == "skill":             # M12 — 스킬북 한 줄 · 스킬 8줄(누르면 팝업)
            put_row("skill_books", "equipped", False, None)
            for d in SKILLS:
                lv = self.skillLv(d["id"]); on = d["id"] in self.G["skills"]["slots"]
                put_row("skill", "equipped" if on else ("buy" if lv else "off"), lv > 0, d["id"])
        elif self.tab == "stat":
            for s in [x for x in STATS if x["id"] not in GEAR_ONLY_STATS]:   # M4 4.3
                cost = self.statCost(s["id"])
                put_row("stat", "buy", self.G["parts"] >= cost, s["id"])
        else:
            # M10 2.2 — 환생 탭: 훈장 · 환생하기 · 남는 것 · 처음으로
            put_row("rebirth_info", "equipped", False, None)
            put_row("rebirth_go", "buy", self.canRebirth(), None)
            for d in MEDAL_PERKS:   # M27 — 훈장 상점 6줄
                full = self.perkLv(d["id"]) >= d["max"]
                put_row("perk_" + d["id"], "buy", (not full) and self.medalsFree() >= self.perkCost(d["id"]), None)
            put_row("rebirth_title", "ghost", False, None)    # M15 — 칭호(보기만)
            put_row("rebirth_record", "ghost", False, None)   # M15 — 기록판(보기만)
            put_row("rebirth_keep", "ghost", False, None)
            put_row("rebirth_reset", "ghost", False, None)
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
        self.questProgress("kill", 1)                      # 지시 #151
        if z["boss"]:
            self.questProgress("boss", 1)
        self.killIndex += 1
        # M3 4.2 — 단계 클리어 일시금. 구역을 넘는 마지막 칸에서는 안 준다.
        if (self.killIndex % self.stageKills(self.G["zone"]) == 0
                and self.killIndex < self.zoneKills(self.G["zone"])):
            self.questProgress("stage", 1)
            self.moveT = STAGE_WALK_SEC                    # M13 — 다음 단계까지 걷는다
            # M6 2.1 — 단계 드랍 없음
            first = self.firstClear(self.G["zone"] * STAGES_PER_ZONE + self.killIndex // self.stageKills(self.G["zone"]))
            self.G["plans"] = self.G.get("plans", 0.0) + (STAGE_PLANS if first else RECLEAR_PLANS)   # M6 7.1 — 개수(광고·수입 안 곱함)
        if z["boss"]:
            first = self.firstClear(self.G["zone"] * STAGES_PER_ZONE + STAGES_PER_ZONE)
            if first:
                self.G["plans"] = self.G.get("plans", 0.0) + BOSS_PLANS
            self.G["books"] = (self.G.get("books") or 0) + (BOSS_BOOKS_FIRST if first else BOSS_BOOKS_AGAIN) + max(0, (self.G.get("loop") or 1) - 1)   # M12
            self.campMats(MATS_BOSS * max(1, self.G.get("loop") or 1))   # M28 — 자재
        if self.killIndex >= self.zoneKills(self.G["zone"]):
            self.killIndex = 0
            if self.farm and self.G["zone"] + 1 == self.farm["zone"]:   # M14 — 보강 중이면 같은 구역 한 번 더
                if self.playerDPS() < self.farm["dps"] and self.farm["t"] < FARM_MAX_SEC:
                    self.moveT = STAGE_WALK_SEC
                    self.G["kills"] = self.killIndex
                    return
                self.farm = None
            self.moveT = ZONE_TRAVEL_SEC if self.G["zone"] < ZONE_COUNT else STAGE_WALK_SEC   # M13 — 다음 구역으로
            if self.G["zone"] < ZONE_COUNT:
                self.G["zone"] += 1
                self.questProgress("zone", 1)
                self.G["bestZone"] = max(self.G["bestZone"], self.G["zone"])
                if self.G["zone"] > (self.G.get("peakZone") or 1):
                    self.G["books"] = (self.G.get("books") or 0) + ZONE_BOOKS   # M14 2.1
                    self.campMats(MATS_ZONE)   # M28
                self.G["peakZone"] = max(self.G.get("peakZone") or 1, self.G["zone"]); self.unlockSkills()   # M12
                del self.zombies[:]
                self.shots = 0
        self.G["kills"] = self.killIndex

    def stepCombat(self, dt):
        hadTarget = len(self.zombies) > 0
        if self.moveT > 0:
            self.moveT = max(0.0, self.moveT - dt)   # M13
        if self.farm:
            self.farm["t"] += dt                     # M14

        self.spawnTimer -= dt
        ttk = self.zoneHP(self.G["zone"]) / max(1e-6, self.playerDPS())
        spawnGap = min(2.0, max(0.35, ttk * 0.9))
        sk = self.stageKills(self.G["zone"])
        remaining = min(self.zoneKills(self.G["zone"]) - self.killIndex, sk - self.killIndex % sk)   # M2 벽 · M13 지금 단계에 남은 만큼만
        if self.moveT <= 0 and self.spawnTimer <= 0 and len(self.zombies) < min(MAX_ONSCREEN_ZOMBIES, remaining):
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
                dmg = self.hitDamage()
                self.dmgShot += dmg                          # 계수기(원본에 없다)
                self.applyDamage(dmg)
                self.pierceShot(dmg)                         # M12 관통탄
        if not self.zombies:
            self.attackTimer = interval
        self.stepSkills(dt)                                  # M12 — 스킬 자동 발동

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
        self.moveT = 0.0                                   # M13
        if self.G["zone"] < frm:
            self.farm = {"zone": frm, "dps": self.playerDPS() * FARM_GAIN, "t": 0.0}   # M14
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
        self.moveT = 0.0                                   # M13
        self.farm = None                                   # M14
        del self.zombies[:]
        self.shots = 0
        self.reviveOffer = None
        return True

    def step(self, dt):
        """`frame()` 의 고정 시간 간격 한 칸. 시계도 같이 민다."""
        self.stepCombat(dt)
        self.campTick(self.now_ms)   # M28 — 원본은 frame() 에서 Date.now() 로
        self.questProgress("play", dt)   # 지시 #187 — 원본은 frame() 의 tickRecords 옆
        self.t += dt
        self.now_ms += dt * 1000

    # ---- 오프라인 ----
    def partsPerSecondEstimate(self):
        ttk = self.zoneHP(self.G["zone"]) / max(1e-6, self.playerDPS())
        return self.zoneReward(self.G["zone"]) * self.statOf("inc") / max(ttk, 0.35)

    def applyOffline(self):
        elapsed = max(0.0, (self.now_ms - (self.G.get("lastSeen") or self.now_ms)) / 1000.0)
        capped = min(elapsed, self.offlineMaxHours() * 3600)   # M27 야간 경계
        if capped < 60:
            return None
        gain = self.partsPerSecondEstimate() * capped * (OFFLINE_RATE + self.campEff("offline"))   # M28 발전소
        self.G["parts"] += gain
        # M3 5 — 설계도도 같이 쌓인다 (원본과 같다)
        # M6 2.1 — 설계도 없음(단계·과제만)
        return dict(elapsed=elapsed, capped=capped, gain=gain, plans=bp,
                    cappedHit=elapsed > capped + 1, doubled=False)


# ── 자동구매 1런 — 감사가 매번 다시 짜던 절차를 여기 고정한다 ────────
# ---- 병렬 실행 (2026-09-18, 지시 #130) ----
# 배터리가 1시간 30분 걸렸다 — 축 가치 하나가 51분(20시드×8구성=160판, 한 판 24초, 한 코어). 이 PC 는 12코어.
# 시드마다 독립이므로 프로세스로 나눠 돈다. **결과는 순차와 같아야 한다** — tools/selftest_checks 가 아니라 measurements/parallel-eq-*.json 이 증명.
# 도구가 쓰던 모듈 수준 덮어쓰기(WALL_KILL_MULT, STATS cost0 잠금)와 감싸기(on_buy, questProgress)는
# 자식 프로세스에 안 옮겨가므로 여기서 인자로 받아 자식 안에서 적용한다.
LOCKED_COST = 1e18


def _worker(args):
    seed, kw, overrides, lock_stat, want_buys, want_quest = args
    import sys as _sys
    S = _sys.modules[_worker.__module__]
    # 덮어쓴 것은 반드시 되돌린다 — 풀의 자식은 여러 일을 이어 받고, workers=1 이면 이 프로세스다 (parallel_eq 가 잡았다: 잠금이 다음 경로로 샜다)
    keep_over = {k: getattr(S, k) for k in (overrides or {})}
    keep_cost = {st["id"]: st["cost0"] for st in S.STATS}
    for k, v in (overrides or {}).items():
        setattr(S, k, v)
    if lock_stat:
        for st in S.STATS:
            if st["id"] == lock_stat:
                st["cost0"] = LOCKED_COST
    kw = dict(kw or {})
    buys = []
    if want_buys:
        kw["on_buy"] = lambda t, z, bid, c: buys.append((t, z, bid, c))
    hits = {}
    orig = S.Sim.questProgress
    if want_quest:
        def qp(self, qid, n, _o=orig, _h=hits):
            _o(self, qid, n)
            if qid in S.QUEST_NEEDS and self.G["qd"].get(qid, 0) >= S.QUEST_NEEDS[qid] and qid not in _h:   # 지시 #187 — 일일(qd)
                _h[qid] = self.t / 60.0
        S.Sim.questProgress = qp
    try:
        r = S.auto_run(seed=seed, **kw)
    finally:
        S.Sim.questProgress = orig
        for k, v in keep_over.items():
            setattr(S, k, v)
        for st in S.STATS:
            st["cost0"] = keep_cost[st["id"]]
    s = r.pop("sim")
    r["income"] = dict(getattr(s, "income", {}) or {})
    r["G"] = s.G
    r["buys"] = buys
    r["quest_hits"] = hits
    return r


def run_many(seeds, kw=None, overrides=None, lock_stat=None, want_buys=False, want_quest=False, workers=None):
    """seeds 를 프로세스로 나눠 auto_run 을 돈다. 순서는 seeds 그대로. `sim` 대신 income·G·buys·quest_hits 를 준다.
    workers=1 이면 이 프로세스에서 순차로(비교·디버그용)."""
    jobs = [(sd, kw, overrides, lock_stat, want_buys, want_quest) for sd in seeds]
    if workers == 1:
        return [_worker(j) for j in jobs]
    import os as _os
    from concurrent.futures import ProcessPoolExecutor
    n = workers or max(1, min(len(jobs), (_os.cpu_count() or 2) - 1))
    with ProcessPoolExecutor(max_workers=n) as ex:
        return list(ex.map(_worker, jobs))


def auto_run(seed=1, max_min=120, buy_every=0.5, dt=FIXED_STEP,
             offline_every_min=None, offline_hours=8, on_buy=None, focus_duty=None,
             stop_zone=None, now_ms=None, sim=None, claim=False, camp=False):
    """가장 싼 것부터 계속 사면서 구역 10 까지 간다.

    `offline_every_min` 을 주면 그만큼 놀고 나서 `offline_hours` 시간 자리를 비운다.
    예측 B4(오프라인 계수를 2배로 바꿔도 진행이 20% 넘게 흔들리지 않는다)를 재는 데 쓴다.

    `on_buy(t초, 구역, 산것, 값)` 을 주면 살 때마다 부른다 — 업그레이드 간격을 재는 데 쓴다.
    `focus_duty=(3, 20)` 을 주면 20초마다 3초씩 집중 사격을 켠다 (M4 2).

    돌아오는 값: 구역별 도달 시각(분) · 벽(10분 넘게 정체한 구역) · 사망 수 · 총 분."""
    s = Sim(seed=seed, now_ms=now_ms) if sim is None else sim     # now_ms: 시간대 과제를 재려고 시작 시각을 옮길 때만 (tools/quest_pace.py)
    if sim is not None:
        s.t = 0.0          # M10 3.2 — 이어 돌리기(환생 뒤 두 번째 판, tools/rebirth_check.py). t 는 재는 시계일 뿐 — 게임 시각은 now_ms 가 이어진다
    s.G["hp"] = s.maxHP()
    zone_at, wall = {1: 0.0}, {}
    deaths, buyT, stuck_from, last_zone = 0, 0.0, 0.0, 1
    idle_buy = 0          # 살 수 있는데 안 산 매수 틱 (c22 가 읽는다)
    idle_kind = {"parts": 0, "plans": 0, "up": 0}   # M6 4.1 — 어느 재화·행동에서 헛돌았는지 (c22 가 같이 읽는다)
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
            if camp:
                s.campAuto()   # M28 — 캠프를 바로바로 짓는 사람(측정 옵션 — 기본 곡선은 짓지 않는다)
            if claim:
                s.claimAll()   # 지시 #187 — 퀘스트 보상을 바로바로 받는 사람(측정 옵션 — 기본 곡선은 받지 않는다)
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
                    if st.get("cap") is not None and s.statOf(st["id"]) >= st["cap"] - 1e-9:
                        continue          # M6 1.2 — 상한에 닿은 축도 후보가 아니다 (c22 가 잡았다: 1121 헛돈틱)
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

                # M6 7.2 — 뽑기 강화 매수는 없어졌다(입수 레벨은 설계도 사용량).
                # M6 2.2/4.1 — 설계도는 뽑기에 쓴다. 10회가 되면 10회, 아니면 1회. 뽑은 뒤 ▲(더 좋은 것)를 낀다.
                # M12 3.2 — 가짜 사람은 가장 늦게 해금된(센) 스킬 4개를 낀다
                want = sorted([d["id"] for d in SKILLS if s.skillLv(d["id"])], key=lambda sid: -s.skillDef(sid)["unlock"])[:SKILL_SLOTS]
                if set(x for x in s.G["skills"]["slots"] if x) != set(want):
                    s.G["skills"]["slots"] = want + [None] * (SKILL_SLOTS - len(want))
                # M12 — 스킬북: 낀 스킬 중 레벨이 가장 낮은 것부터 올린다(해금되면 게임이 빈 칸에 낀다)
                eq = [sid for sid in s.G["skills"]["slots"] if sid and s.skillLv(sid) < SKILL_LV_MAX]
                if eq:
                    low = min(eq, key=lambda sid: s.skillLv(sid))
                    if s.skillUp(low):
                        bought = True
                n = 10 if s.G.get("plans", 0.0) >= s.gachaCost(10) else (1 if s.G.get("plans", 0.0) >= s.gachaCost(1) else 0)
                if n and s.pullGacha(n):
                    bought = True
                    s.gachaResult = None
                    s.fuseAll(); s.equipBest()       # M10 — 뽑은 뒤 일괄 융합·최고 장착(사람이 누르는 두 버튼)
                    if on_buy:
                        on_buy(s.t, s.G["zone"], "G:%d" % n, s.gachaCost(n))


            # **자가 고장 났는지 자기가 센다.** 매수를 끝낸 직후에는 살 수 있는 게
            # 하나도 남아 있으면 안 된다 — 남았다면 이 가짜 사람이 돈을 쥐고 안 쓴 것이다.
            # 2026-09-16 에 바로 그 일이 이틀 동안 조용히 있었다 (cases/2026-09-16-22).
            # checks/c22 가 이 수를 읽는다. 여기서 세는 이유는 **매수 줄이 하나뿐이어야**
            # 검사와 도구가 갈라지지 않기 때문이다.
            if any(s.statCost(st["id"]) <= s.G["parts"]
                   for st in STATS if st["id"] not in GEAR_ONLY_STATS
                   and not (st.get("cap") is not None and s.statOf(st["id"]) >= st["cap"] - 1e-9)):
                idle_buy += 1; idle_kind["parts"] += 1
            elif s.G.get("plans", 0.0) >= s.gachaCost(1):       # M6: 뽑을 수 있는데 안 뽑았다
                idle_buy += 1; idle_kind["plans"] += 1
            # M6 7.2 — 'up'(강화) 칸은 항상 0 — 강화 매수가 없다. c22 호환으로 키는 둔다.
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
                idle_buy=idle_buy, idle_kind=idle_kind, sim=s)


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
