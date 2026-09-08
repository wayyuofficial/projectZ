/* 밸런스 시뮬레이션 — 게임의 **실제 전투 루프**로 1런을 돌린다
 *
 * 쓰는 법: game/index.html 을 브라우저에서 열고 콘솔에 붙여 넣는다.
 * 결과를 measurements/balance-YYYY-MM-DD.json 에 남긴다 (R002).
 *
 * 2026-09-08 개정 — 근사 모델을 버렸다.
 *   예전 판은 "접촉 좀비 수 = 상한 × (1 - 스폰간격/처치시간)" 같은 수식으로 근사했다.
 *   그 모델이 만든 "벽: 구역9 에서 32분 정체" 는 **게임에는 없는 현상**이었다.
 *   실제 루프로 돌려보니 접촉 피해를 8배로 올려도 진행 곡선이 거의 안 변했다
 *   (구역10 도달 68~72분). 근사가 실제와 달랐던 것이다.
 *   그래서 이제 stepCombat 을 그대로 돌린다.
 *
 * 한계 (숨기지 않는다):
 *  - 구매는 0.5초마다 "살 수 있는 것 중 가장 싼 것"을 산다. 사람은 다르게 산다.
 *  - 죽으면 즉시 부활시킨다. 사람은 광고를 보거나 잠시 멈춘다.
 *  - 오프라인 보상은 넣지 않는다.
 */
(function () {
  const MAX_MIN = 120;
  const step = 1 / 60;

  G = freshState(); G.hp = maxHP();
  zombies.length = 0; shots.length = 0; killIndex = 0; dead = false;
  spawnTimer = 0; acc = 0;   // attackTimer 는 손대지 않는다. 손대면 첫 타격 지연 수정이 무효가 된다

  const zoneAt = { 1: 0 }, wall = {};
  let t = 0, deaths = 0, buyT = 0, stuckFrom = 0, lastZone = 1;

  while (t < MAX_MIN * 60 && G.zone < ZONE_COUNT) {
    stepCombat(step); t += step;

    if (dead) { deaths++; revive(); }

    buyT += step;
    if (buyT >= 0.5) {
      buyT = 0;
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
    }

    if (G.zone !== lastZone) {
      const held = t - stuckFrom;
      if (held > 600) wall[lastZone] = +(held / 60).toFixed(0);   // 10분 넘게 머물면 벽
      lastZone = G.zone; stuckFrom = t;
    }
    if (zoneAt[G.zone] === undefined) zoneAt[G.zone] = t;
  }
  if (t - stuckFrom > 600) wall[G.zone] = +((t - stuckFrom) / 60).toFixed(0);

  const 분 = {};
  for (const z in zoneAt) 분[z] = +(zoneAt[z] / 60).toFixed(1);

  G = freshState(); zombies.length = 0; shots.length = 0; killIndex = 0; dead = false;
  return { 구역별_도달_분: 분, 벽_정체분: wall, 최종구역: G.zone,
           사망횟수: deaths, 총_소요분: +(t / 60).toFixed(1) };
})();
