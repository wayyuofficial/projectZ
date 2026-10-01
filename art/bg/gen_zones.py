# -*- coding: utf-8 -*-
"""M8 (지시 #147) — 구역 1~30 배경을 나노바나나로 도트 그래픽 생성. 구역 1 은 이미 만든 city_512.png.
   화풍 통일: 구역 1 을 --ref 로 넣는다. 이미 있는 파일은 건너뛴다(다시 돌려도 과금 안 됨).
   쓰는 법: python art/bg/gen_zones.py"""
import os, subprocess, sys, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = r"D:\nanobanana\nanobanana.py"
REF = os.path.join(HERE, "city_512.png")
STYLE = ("Same pixel art style and palette as the reference image. 16-bit retro pixel art, crisp hard-edged pixels, "
         "side-scrolling 2D game background seen from the side. The lower fifth is a flat walkable floor running straight across the full width. "
         "Upper third is empty sky or dark ceiling with haze so it can be cropped. Muted, desaturated, low contrast so game characters stand out in front. "
         "No characters, no people, no zombies, no animals, no text, no letters, no UI, no border. Scene: ")
ZONES = {
  2: "abandoned shopping alley, shattered shop windows, fallen shop signs, half-closed rolling shutters, trash and rubble, grey overcast dawn",
  3: "stalled elevated highway overpass with a long line of abandoned cars, a broken bridge pier, bent road signs, grey light with thin fog",
  4: "burned-out gas station, scorched canopy, overturned tanker truck, ruined convenience store, soot-stained ground, grey smoky sky",
  5: "large city hall plaza, toppled statue, sandbag barricades, big damaged government building in the back, cloudy morning",
  6: "subway station entrance at street level, stairs going down, broken canopy, knocked-over ticket gates, dark teal tint",
  7: "underground subway platform, stopped train with open doors, white tiled walls, flickering fluorescent lights, dark teal",
  8: "dark subway rail tunnel, tracks on the floor, cables along the walls, small red emergency lights, deep blue-black",
  9: "underground shopping arcade, closed shutters, fallen mannequins, broken direction signs, dim teal light",
  10: "huge subway transfer hall, very high ceiling, stopped escalators, collapsed departure board, light beams through ceiling cracks, teal",
  11: "logistics warehouse yard, stacked shipping containers, abandoned forklift, large shutter doors, hazy smoggy daylight",
  12: "abandoned factory assembly line interior, conveyor belts, idle robot arms, hanging chains, rusty orange-brown light",
  13: "chemical plant, leaking drums, pipes and storage tanks, faint sickly green vapor, rust and dull lime colors",
  14: "harbor dock, cargo cranes, a grounded rusty cargo ship, rusted containers, cloudy orange sky",
  15: "power plant with cooling towers, transmission towers, snapped power lines, smoggy orange sunset",
  16: "highway rest stop, abandoned bus, fuel pumps, small roadside diner, foggy afternoon",
  17: "abandoned farm, collapsed barn, dry dead cornfield, rusty tractor, olive tones with fog",
  18: "dead forest, bare twisted trees, fallen logs, an abandoned car among the trees, olive green with thick fog",
  19: "swamp, shallow water pools on muddy ground, reeds, a half-sunken road sign, wooden plank walkway, murky green-brown",
  20: "collapsed dam, huge cracked concrete wall, drained riverbed floor, broken sluice gates, cold grey fog",
  21: "refugee camp, torn tents, abandoned luggage, burnt-out campfires, khaki sunset",
  22: "quarantine checkpoint, barbed wire fences, boom barrier, watchtower, warning signs without readable text, sunset",
  23: "military field hospital, white tents, stretchers, IV stands, parked ambulance, sunset light on white canvas",
  24: "military base airstrip, crashed helicopter, hangar, armored vehicles, red sunset",
  25: "giant concrete quarantine wall with a huge steel gate, searchlights, dusk",
  26: "outskirts of a research complex at night, hazard signs without text, abandoned hazmat suits, fences, decontamination tunnel, teal emergency lights",
  27: "research lab lobby at night, shattered glass walls, reception desk, red rotating warning lights, teal and red",
  28: "underground lab, rows of glass culture tanks, pipes, broken glass tubes, glowing teal light",
  29: "containment wing, sealed heavy doors, organic fleshy growth spreading over the walls, teal and blood red",
  30: "final containment chamber, one giant central culture tank, the whole room covered in organic tissue, pulsing red light with teal accents",
}
os.makedirs(os.path.join(HERE, "zones"), exist_ok=True)
z1 = os.path.join(HERE, "zones", "z01.png")
if not os.path.exists(z1):
    shutil.copy2(REF, z1)
env = dict(os.environ, PYTHONIOENCODING="utf-8")
for z, scene in ZONES.items():
    out = os.path.join(HERE, "zones", "z%02d.png" % z)
    if os.path.exists(out):
        print("건너뜀", z, flush=True); continue
    for attempt in range(2):
        r = subprocess.run([sys.executable, TOOL, STYLE + scene, "--ref", REF, "--aspect", "1:1", "--out", out],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        last = (r.stdout + r.stderr).strip().splitlines()[-1:] or [""]
        print(z, last[0], flush=True)
        if os.path.exists(out):
            break
print("끝")
