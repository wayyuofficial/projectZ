# -*- coding: utf-8 -*-
"""M12 2.1 (지시 #160) — 스킬 아이콘 시트(나노바나나 flash 512px). sheet_icons_a.png 를 ref 로 화풍(테두리·명암)을 맞춘다.
   읽는 순서(4칸씩): 집중 사격·수류탄·아드레날린·응급처치 / 화염병·관통탄·자동 포탑·지원 사격 / 스킬북·스킬 탭·환생 탭.
   있으면 건너뛴다(--force 로 다시). 쓰는 법: python art/ui/gen_icons_c.py"""
import os, sys, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(HERE, "sheet_icons_c.png")
P = ("Pixel art game UI ICON SHEET: exactly 11 separate icons in a grid of 4 columns (rows of 4, 4, 3), evenly spaced with wide clear gaps, "
     "each icon the same size, centered in its cell, bold dark outline, simple readable silhouette, muted post-apocalyptic palette with one warm accent. "
     "Match exactly the pixel art style, outline thickness and shading of the reference icon sheet. In reading order: "
     "1 crosshair scope with motion lines (focus fire), 2 hand grenade with pin, 3 syringe with red adrenaline liquid and a lightning spark, "
     "4 first aid kit box with green cross, 5 molotov cocktail bottle with burning rag, 6 bullet piercing through two plates (armor piercing), "
     "7 small automatic gun turret on a tripod, 8 falling artillery shell with target marker (air strike), 9 thick worn skill book with a lightning emblem, "
     "10 lightning bolt inside a gear (skills tab), 11 circular arrows around a medal (rebirth). No text, no numbers, no letters, no labels, no frames.")
if os.path.exists(OUT) and "--force" not in sys.argv:
    print("건너뜀"); sys.exit(0)
r = subprocess.run([sys.executable, os.path.join(ROOT, "nanobanana", "nanobanana.py"), P, "--ref", os.path.join(HERE, "sheet_icons_a.png"),
                    "--model", "flash", "--size", "512px", "--aspect", "4:3", "--transparent", "--no-trim", "--out", OUT], capture_output=True, text=True)
print([l for l in (r.stdout + r.stderr).splitlines() if "저장" in l or "오류" in l][-1:])
