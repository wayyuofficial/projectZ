/* 저장 · 마이그레이션 · 오프라인 보상 경로 검증
 *
 * 왜 파이썬 검사가 아니라 이 파일인가:
 *   이 경로는 브라우저 안에서만 돌아간다. 파이썬으로는 실행할 수 없다.
 *   미리보기(data: URL)에서는 localStorage 가 막히므로 가짜 저장소를 끼워 넣는다.
 *
 * 쓰는 법: game/index.html 을 브라우저에서 열고 콘솔에 이 파일 내용을 **그대로** 붙여 넣는다 — 고쳐서 넣지 않는다.
 *          결과를 measurements/storage-YYYY-MM-DD.json 에 남긴다 (R002). 기록의 항목 목록은 이 스크립트의 결과 배열 그대로다.
 *          (24차 감사: 기록의 v1 값이 4칸인데 스크립트는 3칸이었다 — 국소 수정본을 돌렸던 것. 스크립트를 실행본에 맞췄다.)
 *          게임을 고쳤는데 이 기록이 낡으면 checks/c9_measurement_freshness.py 가 잡는다.
 */
(function () {
  const store = {};
  const shim = {
    getItem: k => (k in store ? store[k] : null),
    setItem: (k, v) => { store[k] = String(v); },
    removeItem: k => { delete store[k]; },
    clear: () => { for (const k in store) delete store[k]; }
  };
  try { Object.defineProperty(window, 'localStorage', { value: shim, configurable: true }); }
  catch (e) { return { 오류: '가짜 저장소를 끼울 수 없다: ' + e }; }

  const R = [];
  const chk = (name, cond, val) => R.push({ 항목: name, 결과: cond ? 'OK' : 'FAIL', 값: val });

  // --- 저장과 복원 ---
  G = freshState();
  G.parts = 1234.5; G.zone = 4; G.lv.atk = 7; G.gear.weapon = { slot: 'weapon', type: 'rifle', tier: 2, affixes: [], zone: 4 };   // M6 2.3: 무기는 장비
  saveError = null; save();
  chk('save() 오류 없음', saveError === null, String(saveError));
  chk('저장 키 생성', !!store[SAVE_KEY], SAVE_KEY);

  const before = JSON.parse(JSON.stringify(G));
  G = freshState();
  chk('load() 성공', load() === true, true);
  chk('부품 복원 (소수점까지)', G.parts === 1234.5, G.parts);
  chk('구역 복원', G.zone === 4, G.zone);
  chk('능력치 레벨 복원', G.lv.atk === 7, G.lv.atk);
  chk('무기 등급 복원', G.gear.weapon.type === 'rifle' && G.gear.weapon.tier === 2, JSON.stringify(G.gear.weapon));

  // --- 망가진 저장 ---
  store[SAVE_KEY] = JSON.stringify(Object.assign({}, before, { v: 999 }));
  load();
  chk('모르는 버전 저장은 초기화', G.parts === 0 && G.zone === 1, G.parts + '/' + G.zone);

  // M2: v1(M1) 저장본은 초기화하지 않고 v2 로 끌어올린다 — 사람의 15분이 날아가면 안 된다
  store[SAVE_KEY] = JSON.stringify(Object.assign({}, before, { v: 1, bestZone: undefined }));
  loadError = null;                       // 앞 항목의 실패 문구가 남지 않게 (24차 부수 지적 3: load() 는 loadError 를 스스로 비우지 않는다)
  load();
  chk('v1 저장본이 최신으로 이어진다', G.v === SAVE_VERSION && G.parts === 1234.5 && G.zone === 4 && G.bestZone === 4 && G.gear.weapon.type === 'rifle' && G.gear.weapon.tier === 2 && loadError === null, G.v + '/' + G.zone + '/' + G.bestZone + '/' + loadError);

  // M3 5 — v2 (M2 저장본) 도 설계도 0 으로 이어져야 한다. 무기는 이미 가진 것을 잃지 않는다.
  store[SAVE_KEY] = JSON.stringify(Object.assign({}, before, { v: 2, plans: undefined }));
  loadError = null;
  load();
  chk('v2 저장본이 최신으로 이어진다 (설계도 0)', G.v === SAVE_VERSION && G.parts === 1234.5 && G.zone === 4 && G.plans === 0 && G.gear.weapon.type === 'rifle' && G.gear.weapon.tier === 2 && loadError === null, G.v + '/' + G.zone + '/' + G.plans + '/' + loadError);

  // M4 1 — v3 (M3 저장본) 도 일일 상태가 붙어 이어져야 한다.
  store[SAVE_KEY] = JSON.stringify(Object.assign({}, before, { v: 3, plans: 77, day: undefined, keys: undefined }));
  loadError = null;
  load();
  // M6 7 — v3 의 설계도 77 은 '돈' 이라 v5→v6 에서 옛 1회 값으로 나눠 개수가 된다(수입 레벨 0). 시험도 같은 식으로 센다 — 게임 식을 베끼는 게 아니라 이전 규칙을 밝혀 둔다.
  const plans77 = Math.min(50, Math.floor(77 / Math.max(1, zoneIncome(before.bestZone || 1) * LEGACY_BP_RATIO * LEGACY_GACHA_COST_FRAC)));   // 옛 1회 값은 최고 구역(before 는 1) 기준
  chk('v3 저장본이 최신으로 이어진다 (일일 붙음)', G.v === SAVE_VERSION && G.parts === 1234.5 && G.zone === 4 && G.plans === plans77 && G.keys === KEY_MAX && G.login.streak === 0 && loadError === null, G.v + '/' + G.zone + '/' + G.plans + '/' + G.keys + '/' + loadError);

  // M6 2.3 — v4 (M4·M5 저장본) 의 owned/weapon 은 gear.weapon 과 가방으로 옮겨진다. 가진 무기를 하나도 안 잃는다.
  store[SAVE_KEY] = JSON.stringify(Object.assign({}, before, { v: 4, gear: {}, bag: [], owned: { pipe: 1, rifle: 3, shotgun: 1 }, weapon: 'rifle', gachaLv: undefined }));
  loadError = null;
  load();
  chk('v4 저장본이 최신으로 이어진다 (무기 → 장비)', G.v === SAVE_VERSION && G.gear.weapon.type === 'rifle' && G.gear.weapon.tier === 3
      && G.bag.length === 0 && G.parts > 1234.5 && G.owned === undefined && G.gachaXp === 0 && loadError === null,   // M6 7: gachaLv → gachaXp   // M6 재설계: 가방은 없다 — 옛 무기는 팔려 부품이 된다
      G.gear.weapon.type + '/' + G.gear.weapon.tier + '/' + G.bag.length + '/' + Math.round(G.parts));

  // M6 7 — v5 (M6 2~6 저장본) 의 설계도 '돈' 은 옛 1회 값으로 나눠 개수가 되고(상한 50), 뽑기 강화 단계 3 은 입수 Lv3 문턱 경험치가 된다.
  store[SAVE_KEY] = JSON.stringify(Object.assign({}, before, { v: 5, plans: 1e12, gachaLv: 3, gachaXp: undefined }));
  loadError = null;
  load();
  chk('v5 저장본이 최신으로 이어진다 (설계도 개수·입수 레벨)', G.v === SAVE_VERSION && G.plans === 50 && G.gachaXp === GACHA_XP_NEEDS[2] && curGachaLv() === 3 && G.gachaLv === undefined && loadError === null,
      G.v + '/' + G.plans + '/' + G.gachaXp + '/' + curGachaLv());

  store[SAVE_KEY] = JSON.stringify({ v: SAVE_VERSION, parts: 50 });
  load();
  chk('항목이 빠진 저장 보정', G.zone === 1 && G.lv.reg === 0 && G.gear.weapon.type === 'pipe', JSON.stringify(G.lv));

  store[SAVE_KEY] = '{{{깨진';
  loadError = null;                       // 불러오기 실패는 saveError 가 아니라 loadError 다 (11차 감사 뒤)
  const ok2 = load();
  chk('깨진 저장은 error 로 남고 초기화', ok2 === false && loadError !== null, String(loadError).slice(0, 40));

  // --- 오프라인 보상 ---
  const fresh = (z, atk) => { G = freshState(); G.zone = z; G.lv.atk = atk; };

  fresh(3, 10); G.lastSeen = Date.now() - 30 * 1000;
  chk('30초는 보상 없음', applyOffline() === null, 'null');

  fresh(3, 10); G.lastSeen = Date.now() - 4 * 3600 * 1000;
  const r4 = applyOffline();
  chk('4시간 보상 발생', !!r4 && r4.gain > 0 && !r4.cappedHit, r4 && Math.round(r4.gain));

  fresh(3, 10); G.lastSeen = Date.now() - 20 * 3600 * 1000;
  const r20 = applyOffline();
  chk('20시간은 8시간에서 잘림',
      !!r20 && r20.cappedHit && Math.abs(r20.capped - OFFLINE_MAX_HOURS * 3600) < 2,
      r20 && Math.round(r20.capped / 3600) + '시간');
  chk('8시간 보상 = 4시간의 2배',
      !!r4 && !!r20 && Math.abs(r20.gain / r4.gain - 2) < 0.01,
      r4 && r20 && +(r20.gain / r4.gain).toFixed(3));

  // --- 광고 2배 ---
  offlineReport = r20;
  const g0 = G.parts;
  adReward('offline2x');
  chk('광고 2배가 한 번 먹힘',
      Math.abs(G.parts - g0 - r20.gain) < 1 && offlineReport.doubled === true,
      Math.round(G.parts - g0));
  const g1 = G.parts;
  adReward('offline2x');
  chk('두 번째 광고는 무시', Math.abs(G.parts - g1) < 1e-9, Math.round(G.parts - g1));

  // 원복
  G = freshState(); offlineReport = null;
  zombies.length = 0; shots.length = 0; killIndex = 0;   // `dead` 는 지시 #35(자동 후퇴)로 사라졌다

  return { 실패: R.filter(r => r.결과 === 'FAIL').length, 전체: R.length, 결과: R };
})();
