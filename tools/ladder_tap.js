// M10 4.1 — 부위 사다리 팝업(40칸 + 일괄 융합·닫기)의 탭 대상이 MIN_TAP_CSS 를 지키는지. 브라우저에서 잰다.
// 거울(tools/sim_port.py)에는 팝업이 없다(그리기·입력 쪽) — 그래서 tap_check.py 와 따로다.
// 뷰포트 280~500 x 560~1000 을 20·40px 씩 훑고, 각 뷰포트에서 진짜 fitGame·buildButtons 를 부른다.
// 쓰는 법: NODE_PATH=$(npm root -g) node tools/ladder_tap.js [--out measurements/ladder-tap-YYYY-MM-DD.json]
// 종료 코드: 가장 작은 칸이 선 아래면 1.
const { chromium } = require('playwright'); const fs = require('fs'); const path = require('path'); const crypto = require('crypto');
(async () => {
  const game = path.join(__dirname, '..', 'game', 'index.html');
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' }).catch(() => chromium.launch());
  const p = await b.newPage(); const errs = []; p.on('pageerror', (e) => errs.push(e.message));
  await p.goto('file://' + game); await p.waitForTimeout(600);
  let best = null, n = 0, line = null;
  for (let vw = 280; vw <= 500; vw += 20) for (let vh = 560; vh <= 1000; vh += 40) {
    await p.setViewportSize({ width: vw, height: vh });
    const r = await p.evaluate(() => {
      fitGame(); slotPopup = { slot: 'weapon' }; buildButtons();
      const per = cssW / GAME_W, out = [];
      for (const bt of buttons) if (bt.tone !== 'scrim') out.push({ k: bt.cell, label: bt.label, w: bt.w * per, h: bt.h * per });
      slotPopup = null; buildButtons();
      return { line: MIN_TAP_CSS, out };
    });
    line = r.line;
    for (const t of r.out) { n++; const s = Math.min(t.w, t.h); if (!best || s < best.s) best = { s, 뷰포트: [vw, vh], 대상: t.k !== undefined ? '칸 ' + t.k : t.label, 폭: +t.w.toFixed(2), 높이: +t.h.toFixed(2) }; }
  }
  await b.close();
  const ok = best.s >= line && errs.length === 0;
  console.log('사다리 팝업 탭 대상 표본 ' + n + '개');
  console.log('가장 작은: ' + best.s.toFixed(2) + ' CSS px (선 ' + line + ') ' + JSON.stringify(best));
  console.log('콘솔 오류: ' + errs.length + (errs.length ? ' ' + errs.slice(0, 2).join(' | ') : ''));
  console.log('결과: ' + (ok ? '통과' : '**미달**'));
  const i = process.argv.indexOf('--out');
  if (i > 0) {
    const stamp = crypto.createHash('sha256').update(fs.readFileSync(game)).digest('hex').slice(0, 16);
    fs.writeFileSync(process.argv[i + 1], JSON.stringify({ 측정일: new Date().toISOString().slice(0, 10), 대상: '부위 사다리 팝업 탭 대상(M10)', 빌드도장: stamp,
      도구: 'tools/ladder_tap.js', 표본: n, 최소_CSS_px: +best.s.toFixed(2), 가장_작은_자리: best, 선: line, 콘솔오류: errs.length, 결과: ok ? '통과' : '미달',
      판정하지_않는다: '판정은 검증자·사람 몫이다.' }, null, 2));
    console.log('기록: ' + process.argv[i + 1]);
  }
  process.exit(ok ? 0 : 1);
})();
