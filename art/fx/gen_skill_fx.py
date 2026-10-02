# -*- coding: utf-8 -*-
"""M12 2.2 (지시 #160) — 스킬 효과 시트(나노바나나 flash 512px). 무기 시트(art/weapons/sheet_a.png)를 ref 로.
   2줄 × 2칸: 손 수류탄 · 초록 회복 십자 빛 / 삼각대 자동 포탑(오른쪽을 본다) · 아래로 떨어지는 포탄. 있으면 건너뛴다(--force).
   쓰는 법: python art/fx/gen_skill_fx.py → python art/fx/build_fx.py"""
import os, sys, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(HERE, "sheet_skills.png")
P = ("Pixel art game effect SPRITE SHEET, exactly 4 separate sprites in a 2x2 grid with wide clear gaps, side view, bold dark outline, "
     "match exactly the pixel art style and shading of the reference weapon sheet. Top-left: a green hand grenade with pin. "
     "Top-right: a glowing bright green medical cross with soft green glow particles (healing). "
     "Bottom-left: a small automatic machine gun turret on a tripod, barrel pointing RIGHT. "
     "Bottom-right: an artillery shell falling straight DOWN, nose pointing down, small fire trail on top. No text, no letters, no frames, no ground.")
if os.path.exists(OUT) and "--force" not in sys.argv:
    print("건너뜀"); sys.exit(0)
r = subprocess.run([sys.executable, os.path.join(ROOT, "nanobanana", "nanobanana.py"), P, "--ref", os.path.join(ROOT, "art", "weapons", "sheet_a.png"),
                    "--model", "flash", "--size", "512px", "--aspect", "1:1", "--transparent", "--no-trim", "--out", OUT], capture_output=True, text=True)
print([l for l in (r.stdout + r.stderr).splitlines() if "저장" in l or "오류" in l][-1:])
