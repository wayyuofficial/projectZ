/* 밸런스 시뮬레이션 — 게임의 실제 함수로 1런을 돌린다
 *
 * 쓰는 법: game/index.html 을 브라우저에서 열고 콘솔에 붙여 넣는다.
 * 결과를 measurements/balance-YYYY-MM-DD.json 에 남긴다 (R002).
 *
 * 2026-09-08 검증자 지적: 이 스크립트가 저장소에 없어서 기록된 값을 재현할 수 없었다.
 * 원칙 9 — 조사는 한 번 하고 결과를 파일로 남긴다. 스크립트도 파일이다.
 *
 * 한계 (숨기지 않는다):
 *  - 보스를 따로 모델링하지 않는다. 평균 처치율로만 본다. 보스 돌진 패턴은 반영되지 않는다.
 *  - 접촉 좀비 수를 스폰 간격과 처치 시간의 비로 근사한다. 실제 배치·이동은 무시한다.
 *  - 탐욕 구매(가장 싼 것부터)를 가정한다. 사람은 다르게 살 수 있다.
 */
(function () {
  G = freshState();
  let t = 0, kills = 0;
  const zoneAt = { 1: 0 }, walls = {};
  let stuck = 0;
  const dt = 1;

  while (t < 48 * 3600 && G.zone <= ZONE_COUNT) {
    // 살 수 있는 것 중 가장 싼 것을 산다
    let bought = true;
    while (bought) {
      bought = false;
      let id = null, cheapest = Infinity;
      for (const s of STATS) {
        const c = statCost(s.id);
        if (c <= G.parts && c < cheapest) { cheapest = c; id = s.id; }
      }
      for (const w of WEAPON_TYPES) {
        const c = weaponUpgradeCost(w.id);
        if (c !== null && c <= G.parts && c < cheapest) { cheapest = c; id = 'W:' + w.id; }
      }
      if (id) bought = id.indexOf('W:') === 0 ? buyWeapon(id.slice(2)) : buyStat(id);
    }

    const zhp = zoneHP(G.zone), zdps = zoneDPS(G.zone), rw = zoneReward(G.zone);
    const ttk = zhp / Math.max(1e-9, playerDPS());
    const gap = Math.min(2, Math.max(0.35, ttk * 0.9));      // 게임의 적응형 스폰 간격과 같은 식
    const contact = Math.max(0, Math.min(MAX_ONSCREEN_ZOMBIES,
      MAX_ONSCREEN_ZOMBIES * (1 - Math.min(1, gap / ttk))));
    const incoming = contact * zdps;
    const killRate = 1 / Math.max(ttk, 0.35);

    G.parts += rw * killRate * dt;

    // 죽기 전에 한 구역(10마리)을 잡을 수 있는가
    const ok = incoming <= regenPerSec() ||
      (maxHP() / (incoming - regenPerSec())) * killRate >= KILLS_PER_ZONE;

    if (ok) {
      kills += killRate * dt; stuck = 0;
      while (kills >= KILLS_PER_ZONE && G.zone < ZONE_COUNT) {
        kills -= KILLS_PER_ZONE; G.zone++; zoneAt[G.zone] = t;
      }
      if (G.zone >= ZONE_COUNT) { if (zoneAt[10] === undefined) zoneAt[10] = t; break; }
    } else {
      kills = 0; stuck += dt;
      if (stuck > 1200) walls[G.zone] = Math.round(stuck / 60);   // 20분 넘게 정체 = 벽
    }
    t += dt;
  }

  const 분 = {};
  for (const k in zoneAt) 분[k] = +(zoneAt[k] / 60).toFixed(1);
  G = freshState();
  return { 구역별_도달_분: 분, 벽_정체분: walls, 총_클리어_시간: +(t / 3600).toFixed(2) };
})();
