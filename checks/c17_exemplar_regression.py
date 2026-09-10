# -*- coding: utf-8 -*-
"""검사가 **좋다고 판정된 산출물**을 떨어뜨리는지.

근거: 불변 원칙 5 — "검사 기준은 과거 좋은 산출물을 떨어뜨리면 안 된다".
`checks/README.md` 가 그동안 이렇게 적고 있었다:

> **원칙 5 미이행** — 과거 산출물이 0건이라 "좋은 산출물을 떨어뜨리지 않는지" 역검증을 못 했다.
> 모든 기준은 현재 **미검증**이다.

2026-09-10 에 사람이 `exemplars/good/` 에 빌드 하나를 "이건 게임이다" 로 등록했다.
이제 역검증이 가능하다.

## 무엇을 하는가

`exemplars/good/*.html` 을 임시 저장소 모양(`game/index.html` 자리)에 놓고,
**게임을 보는 검사들을 그대로 다시 돌린다.** 하나라도 걸리면 이 검사가 실패한다.

**이 검사가 실패하면 산출물이 아니라 검사를 의심한다.** 그게 원칙 5 의 뜻이다.
사람이 좋다고 한 것을 떨어뜨리는 기준은 기준이 틀린 것이다.

## 1순위인 이유
기준이 조용히 엄해지면 그 뒤 만드는 것이 전부 그 기준에 맞춰 휜다.
그걸 잡는 유일한 바깥 기준점이 본보기다.

## 이 검사가 못 막는 것 (숨기지 않는다)
- **본보기가 하나뿐이다.** 그 하나를 통과시키도록 기준을 맞추면 이 검사도 같이 속는다.
- **그림·느낌은 못 본다.** 여기서 돌리는 것은 글자와 숫자를 보는 검사들뿐이다.
  "좋아 보이는가" 는 여전히 사람이 본다.
- 본보기를 사람이 지우거나 바꾸면 이 검사도 같이 바뀐다. 그건 git 이력에 남는다.
"""
NAME = "검사가 좋다고 판정된 산출물을 떨어뜨리는지"
PRIORITY = 1

import io, os, sys, glob, shutil, tempfile, importlib.util

# 게임 HTML 을 보는 검사들. 여기 없는 것(정본·계획·측정·안드로이드)은 본보기와 무관하다.
GAME_CHECKS = ["c2_scope.py", "c3_no_network.py", "c5_save_version.py",
               "c6_single_file.py", "c10_html_meta.py", "c12_draw_order.py"]


def _load(path):
    spec = importlib.util.spec_from_file_location(os.path.basename(path)[:-3], path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def run(root):
    ex = sorted(glob.glob(os.path.join(root, "exemplars", "good", "*.html")))
    if not ex:
        return {"status": "skip",
                "detail": ["exemplars/good/*.html 이 없다 — 사람이 '좋다' 판정한 산출물이 아직 없다",
                           "원칙 5 역검증은 그때까지 미이행이다"]}

    bad = []
    checked = 0
    for src in ex:
        tmp = tempfile.mkdtemp(prefix="c17_")
        try:
            # 본보기를 game/index.html 자리에 놓는다
            os.makedirs(os.path.join(tmp, "game"))
            shutil.copyfile(src, os.path.join(tmp, "game", "index.html"))
            # 검사가 참조하는 정본도 같이 옮긴다 (c2 가 상한을 읽는다)
            canon_src = os.path.join(root, "canon")
            if os.path.isdir(canon_src):
                shutil.copytree(canon_src, os.path.join(tmp, "canon"))

            for name in GAME_CHECKS:
                p = os.path.join(root, "checks", name)
                if not os.path.exists(p):
                    continue
                try:
                    r = _load(p).run(tmp)
                except Exception as e:
                    bad.append("%s : %s 가 터졌다 — %s" % (os.path.basename(src), name, e))
                    continue
                checked += 1
                st = r.get("status")
                if st in ("fail", "error"):
                    bad.append("%s : %s 가 [%s] — %s"
                               % (os.path.basename(src), name, st,
                                  "; ".join(str(x) for x in r.get("detail", []))[:160]))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    if bad:
        bad.append("**사람이 '좋다' 판정한 산출물을 검사가 떨어뜨렸다.**")
        bad.append("산출물이 아니라 **검사를 의심한다** — 불변 원칙 5.")
        bad.append("기준을 정말 엄하게 해야 하면 본보기를 새로 등록하고 사람이 다시 판정한다.")
        return {"status": "fail", "detail": bad}
    return {"status": "ok",
            "detail": ["본보기 %d개 × 검사 %d회 전부 통과 — 기준이 좋은 산출물을 떨어뜨리지 않는다"
                       % (len(ex), checked)]}
