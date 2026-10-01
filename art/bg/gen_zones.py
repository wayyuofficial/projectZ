# -*- coding: utf-8 -*-
"""M8 (지시 #147) — 구역 1~30 배경을 나노바나나로 도트 그래픽 생성. 구역 1 은 이미 만든 city_512.png.
   화풍 통일: 구역 1 을 --ref 로 넣는다. 이미 있는 파일은 건너뛴다(다시 돌려도 과금 안 됨).
   쓰는 법: python art/bg/gen_zones.py"""
import os, subprocess, sys, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.environ.get("NANOBANANA") or (r"D:\nanobanana\nanobanana.py" if os.name == "nt" else os.path.join(os.path.dirname(os.path.dirname(HERE)), "nanobanana", "nanobanana.py"))   # M11: 클라우드는 저장소 안 도구
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
  # M11 (지시 #156·#157) — 구역 31~60: 학교 · 대형 마트 · 놀이공원 · 교도소 · 크루즈선 · 핵발전소
  31: "abandoned school front gate at dusk, closed iron gate pushed open, school bus crashed into the wall, scattered backpacks, warm orange-brown light",
  32: "empty school sports field at dusk, broken soccer goals, running track, toppled bleachers, flagpole without flag, orange-brown haze",
  33: "school hallway interior, rows of lockers hanging open, broken classroom windows, scattered papers, dim orange sunset light through windows",
  34: "school science lab, lab benches, broken beakers and flasks, skeleton model, cracked chalkboard without text, orange-brown dim light",
  35: "school auditorium, rows of seats, stage with torn curtains, fallen spotlights, dusty orange stage light",
  36: "huge supermarket parking lot, abandoned shopping carts, crashed cars, big store front with broken glass doors, sickly yellow-green streetlights",
  37: "supermarket checkout area, row of cash registers, knocked-over candy racks, scattered goods, flickering fluorescent lights, yellow-green",
  38: "supermarket food aisles, tall shelves half empty, fallen products, spilled cans, flickering fluorescent light, yellow-green",
  39: "supermarket frozen storage room, frosted freezers, hanging meat hooks, ice on the floor, cold blue-green light",
  40: "supermarket loading dock, delivery truck, stacked pallets, open warehouse shutter, dim yellow light",
  41: "abandoned amusement park entrance at night, ticket booths, colorful arch gate, broken neon lights, pink and purple glow",
  42: "abandoned carousel plaza at night, broken carousel horses, popcorn stand, scattered balloons, pink and purple neon",
  43: "abandoned roller coaster at night, tall twisted tracks, derailed coaster car, neon lights flickering, pink and purple",
  44: "haunted house attraction at night, fake tombstones, torn ghost decorations, broken spooky facade, purple fog",
  45: "parade street of an amusement park at night, toppled parade float, giant deflated balloon, confetti on the ground, pink and purple neon",
  46: "prison outer perimeter at night, tall barbed wire fences, guard tower with searchlight, grey concrete walls, orange warning lights",
  47: "prison visiting room, glass partitions, telephones, overturned chairs, grey walls, dim orange light",
  48: "prison cell block interior, two floors of cells with open bars, metal walkways, grey concrete, orange alarm lights",
  49: "prison exercise yard at night, basketball hoop, weight benches, chain link fence, searchlight beams, grey and orange",
  50: "solitary confinement wing, heavy steel doors, narrow dark corridor, flickering orange alarm lights, grey concrete",
  51: "cruise ship pier at stormy night, gangway to a huge white cruise ship, abandoned luggage, navy blue and white",
  52: "cruise ship open deck in a storm, deck chairs, empty swimming pool, lifeboats hanging, rain and dark navy sea",
  53: "cruise ship grand ballroom, chandeliers, overturned dining tables, grand staircase, dim navy blue and gold light",
  54: "cruise ship engine room, huge engines, pipes and valves, steam, metal catwalk, dim navy blue light with red warning lamps",
  55: "cruise ship bridge at stormy night, ship wheel and control panels, cracked front windows, lightning over the dark sea, navy blue",
  56: "nuclear power plant front gate at night, security booth, barrier, radiation warning signs without text, eerie green glow",
  57: "nuclear power plant cooling towers at night, steam, cracked concrete, toxic green glow on the ground",
  58: "nuclear power plant turbine hall, giant turbines, pipes, catwalks, flickering lights, green and black",
  59: "nuclear power plant control room, rows of control panels with blinking lights, broken monitors, green warning glow",
  60: "nuclear reactor core chamber, glowing reactor pool, radioactive green light, cracked containment walls, black and toxic green",
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
