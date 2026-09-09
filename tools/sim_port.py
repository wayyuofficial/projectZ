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

## 안 옮긴 것 (여기서 판정하면 안 되는 것)

그리기(`draw*`) · 입력 · 캔버스 · `localStorage` · 화면 배치.
이 포트로 "화면이 이렇게 보인다"를 판정하지 않는다. 그건 사람이나 실기가 한다.

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
        for k, v in re.findall(r"(\w+)\s*:\s*('[^']*'|\"[^\"]*\"|-?[\d.]+)", row.group(1)):
            d[k] = v[1:-1] if v[0] in "'\"" else float(v)
        out.append(d)
    return out


SAVE_VERSION = int(num("SAVE_VERSION"))
ZONE_COUNT = int(num("ZONE_COUNT"))
TIER_MAX = int(num("TIER_MAX"))
MAX_ONSCREEN_ZOMBIES = int(num("MAX_ONSCREEN_ZOMBIES"))
ZONE_HP0, ZONE_HP_G = num("ZONE_HP0"), num("ZONE_HP_G")
ZONE_RW0, ZONE_RW_G = num("ZONE_RW0"), num("ZONE_RW_G")
ZOMBIE_DPS_RATIO = num("ZOMBIE_DPS_RATIO")
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
SURVIVOR_X = num("SURVIVOR_X")
CONTACT_X = SURVIVOR_X + 46          # 원본도 SURVIVOR_X + 46 으로 쓴다
ZOMBIE_GAP = num("ZOMBIE_GAP")
CONTACT_REACH = num("CONTACT_REACH")
SPAWN_X = GAME_W + 36
FIXED_STEP = 1.0 / 60
MAX_STEPS = int(num("MAX_STEPS"))
MAX_GAP = num("MAX_GAP")

STATS = table("STATS")
WEAPON_TYPES = table("WEAPON_TYPES")


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
    "applyDamage": "a42df6ae4cb6cf99",
    "applyOffline": "b7cab65995bd9534",
    "attacksPerSec": "50d4fd5785b29ace",
    "buyStat": "2b0b94e9a15bcaaa",
    "buyWeapon": "0c1bb6b5a33eb755",
    "damageZombie": "9dfa910d5cf6855b",
    "freshState": "d3e150adddd9425b",
    "hitDamage": "78764110ba1a3fdd",
    "isBossKill": "4e70f4e006a8ab2a",
    "killZombie": "f24afd439d608803",
    "maxHP": "85e54826f897f7c7",
    "migrate": "f7ef8c70ad7c767b",
    "partsPerSecondEstimate": "02bde987992b2e2e",
    "playerDPS": "6e388f9e36329ce1",
    "regenPerSec": "73badd17c9fc2857",
    "revive": "34ef58959a8d7729",
    "spawnZombie": "d4054c63f48a4d4a",
    "statCost": "3915c9b212b37571",
    "statOf": "bd53f6155e340e8d",
    "stepCombat": "9a390a08bfe2fae5",
    "weaponPower": "0a8ae8face6a1394",
    "weaponUpgradeCost": "d865ed90770874b1",
    "zoneDPS": "9abab3ae0b004352",
    "zoneHP": "eafea50cbb2f5af6",
    "zoneReward": "60bede52ceeb226c",
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

    def __init__(self, seed=1, state=None, now_ms=1000000000000):
        self.rnd = RNG(seed)
        self.now_ms = now_ms
        self.G = state if state is not None else self.freshState()
        self.zombies = []
        self.shots = 0                 # 궤적은 그리기용이라 개수만 센다
        self.spawnTimer = 0.0
        self.attackTimer = 0.0
        self.killIndex = 0
        self.dead = False
        self.t = 0.0
        self.offlineReport = None
        self.adLog = []

    # ---- 저장 ----
    def freshState(self):
        return dict(v=SAVE_VERSION, parts=0.0, zone=1, kills=0,
                    lv=dict(atk=0, spd=0, hp=0, reg=0), weapon="pipe",
                    owned=dict(pipe=1), hp=100.0, bestZone=1, totalKills=0,
                    lastSeen=self.now_ms, boostUntil=0)

    def migrate(self, raw):
        if not isinstance(raw, dict):
            return self.freshState()
        if raw.get("v") != SAVE_VERSION:
            return self.freshState()
        s = self.freshState()
        for k in list(s.keys()):
            if k in raw:
                s[k] = raw[k]
        lv = dict(atk=0, spd=0, hp=0, reg=0)
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
        return s["base"] * (s["growth"] ** self.G["lv"].get(i, 0))

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
        return self.statOf("spd")

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
    def zoneReward(z):
        return ZONE_RW0 * (ZONE_RW_G ** (z - 1))

    @staticmethod
    def isBossKill(z, idx):
        return (z % BOSS_EVERY == 0) and idx == KILLS_PER_ZONE - 1

    def weaponUpgradeCost(self, wid):
        w = self.weaponOf(wid)
        tier = self.G["owned"].get(wid, 0)
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
    def buyStat(self, i):
        c = self.statCost(i)
        if self.G["parts"] < c:
            return False
        self.G["parts"] -= c
        self.G["lv"][i] = self.G["lv"].get(i, 0) + 1
        return True

    def buyWeapon(self, wid):
        cost = self.weaponUpgradeCost(wid)
        if cost is None or self.G["parts"] < cost:
            return False
        self.G["parts"] -= cost
        self.G["owned"][wid] = self.G["owned"].get(wid, 0) + 1
        self.G["weapon"] = wid
        return True

    # ---- 전투 ----
    def spawnZombie(self):
        if len(self.zombies) >= MAX_ONSCREEN_ZOMBIES:
            return
        boss = self.isBossKill(self.G["zone"], self.killIndex + len(self.zombies))
        hp = self.zoneHP(self.G["zone"]) * (BOSS_HP_MULT if boss else 1)
        self.zombies.append(dict(
            x=SPAWN_X + self.rnd() * 30,
            hp=hp, max=hp, boss=boss,
            speed=17.0 if boss else 24 + self.rnd() * 12,
            held=False, charge=0.0,
            nextCharge=BOSS_CHARGE_EVERY if boss else 0.0))

    def damageZombie(self, z, dmg):
        z["hp"] -= dmg
        if z["hp"] <= 0:
            self.killZombie(z)

    def applyDamage(self, dmg):
        left, guard = dmg, 0
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

    def killZombie(self, z):
        if z not in self.zombies:
            return
        self.zombies.remove(z)
        gain = self.zoneReward(self.G["zone"]) * (BOSS_EVERY if z["boss"] else 1) * self.rewardMult()
        self.G["parts"] += gain
        self.G["totalKills"] += 1
        self.killIndex += 1
        if self.killIndex >= KILLS_PER_ZONE:
            self.killIndex = 0
            if self.G["zone"] < ZONE_COUNT:
                self.G["zone"] += 1
                self.G["bestZone"] = max(self.G["bestZone"], self.G["zone"])
                del self.zombies[:]
                self.shots = 0
        self.G["kills"] = self.killIndex

    def stepCombat(self, dt):
        if self.dead:
            return
        hadTarget = len(self.zombies) > 0

        self.spawnTimer -= dt
        ttk = self.zoneHP(self.G["zone"]) / max(1e-6, self.playerDPS())
        spawnGap = min(2.0, max(0.35, ttk * 0.9))
        remaining = KILLS_PER_ZONE - self.killIndex
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
            self.G["hp"] = 0.0
            self.dead = True
            del self.zombies[:]
            self.shots = 0

    def revive(self):
        self.dead = False
        self.G["hp"] = self.maxHP()
        self.killIndex = 0
        self.G["kills"] = 0
        del self.zombies[:]
        self.shots = 0

    def step(self, dt):
        """`frame()` 의 고정 시간 간격 한 칸. 시계도 같이 민다."""
        self.stepCombat(dt)
        self.t += dt
        self.now_ms += dt * 1000

    # ---- 오프라인 ----
    def partsPerSecondEstimate(self):
        ttk = self.zoneHP(self.G["zone"]) / max(1e-6, self.playerDPS())
        return self.zoneReward(self.G["zone"]) / max(ttk, 0.35)

    def applyOffline(self):
        elapsed = max(0.0, (self.now_ms - (self.G.get("lastSeen") or self.now_ms)) / 1000.0)
        capped = min(elapsed, OFFLINE_MAX_HOURS * 3600)
        if capped < 60:
            return None
        gain = self.partsPerSecondEstimate() * capped * OFFLINE_RATE
        self.G["parts"] += gain
        return dict(elapsed=elapsed, capped=capped, gain=gain,
                    cappedHit=elapsed > capped + 1, doubled=False)


# ── 자동구매 1런 — 감사가 매번 다시 짜던 절차를 여기 고정한다 ────────
def auto_run(seed=1, max_min=120, buy_every=0.5, dt=FIXED_STEP):
    """가장 싼 것부터 계속 사면서 구역 10 까지 간다.

    돌아오는 값: 구역별 도달 시각(분) · 벽(10분 넘게 정체한 구역) · 사망 수 · 총 분."""
    s = Sim(seed=seed)
    s.G["hp"] = s.maxHP()
    zone_at, wall = {1: 0.0}, {}
    deaths, buyT, stuck_from, last_zone = 0, 0.0, 0.0, 1
    while s.t < max_min * 60 and s.G["zone"] < ZONE_COUNT:
        s.step(dt)
        if s.dead:
            deaths += 1
            s.revive()
        buyT += dt
        if buyT >= buy_every:
            buyT = 0.0
            bought = True
            while bought:
                bought = False
                bid, cheap = None, float("inf")
                for st in STATS:
                    c = s.statCost(st["id"])
                    if c <= s.G["parts"] and c < cheap:
                        cheap, bid = c, st["id"]
                for w in WEAPON_TYPES:
                    c = s.weaponUpgradeCost(w["id"])
                    if c is not None and c <= s.G["parts"] and c < cheap:
                        cheap, bid = c, "W:" + w["id"]
                if bid:
                    bought = s.buyWeapon(bid[2:]) if bid.startswith("W:") else s.buyStat(bid)
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
                final_zone=s.G["zone"])


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
    print("60초 런(seed 1): 구역 %d / 처치 %d / 부품 %.1f / hp %.2f"
          % (s.G["zone"], s.G["totalKills"], s.G["parts"], s.G["hp"]))
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
