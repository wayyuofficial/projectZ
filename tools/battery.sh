#!/usr/bin/env bash
# 현재 빌드에서 판정 근거 전부를 저장소 스크립트로 다시 뜬다 (R005). 한 번에, 순서대로.
# 31차 감사(2026-09-17): "battery.sh 가 저장소에 없다 — 예측 M5-B3 와 WBS 5.1 이 없는 도구를 가리킨다." 스크래치에서 여기로 옮겼다.
# 쓰는 법:  bash tools/battery.sh 2026-09-17c      (인자 = 기록 접미사. 같은 이름이면 덮어쓴다 — 비교할 기록은 다른 접미사로)
set -e
cd "$(dirname "$0")/.."
export PYTHONIOENCODING=utf-8
D="${1:?기록 접미사(YYYY-MM-DD 또는 YYYY-MM-DDx)를 줘라}"
python tools/gen_balance_csv.py | tail -1
python tools/curve_check.py    --seeds 20 --out measurements/balance-M4-curve-g-$D.json | tail -2
python tools/upgrade_cadence.py --seeds 20 --out measurements/upgrade-cadence-m4-g-$D.json | tail -3
python tools/axis_value.py     --seeds 20 --max-min 400 --out measurements/axis-value-$D.json | tail -4   # 2026-09-18: 상한 900 이면 한 시간 넘게 걸린다 (지시 #128)
python tools/sell_share.py     --seeds 20 --out measurements/sell-share-$D.json | tail -2   # M10: 판매 비중 판정 은퇴 — c23 기준선(30구역 도달)만
python tools/quest_pace.py     --seeds 20 --out measurements/quest-pace-$D.json | tail -6
for H in 8 16 0; do python tools/quest_pace.py --seeds 20 --start-hour $H --out measurements/quest-pace-h$H-$D.json | tail -1; done
python tools/daily_budget.py             --out measurements/daily-budget-$D.json | tail -3
python tools/gear_roll.py      --n 10000 --out measurements/gear-roll-$D.json | tail -2
python tools/tap_check.py                --out measurements/tap-$D.json | tail -2
python tools/gacha_check.py    --n 20000 --out measurements/gacha-$D.json | tail -3   # M6 4.3 — 확률표 · M10 영원 0(융합으로만)
echo "=== 도장 ==="
python -c "import hashlib,io;print(hashlib.sha256(io.open('game/index.html','rb').read()).hexdigest()[:16])"
echo "저장 시험(test_storage.js)은 브라우저에서 — 파이썬으로 못 돈다."
