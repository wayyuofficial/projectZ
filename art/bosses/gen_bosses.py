# -*- coding: utf-8 -*-
"""보스 시트 생성(나노바나나 flash 512px, 21:9, 한 줄 4프레임: 걷기 2 · 돌진 준비 · 돌진). M9 2.1 · M11 2.4(지시 #157).
   있는 파일은 건너뛴다(--force 로 다시). 쓰는 법: python art/bosses/gen_bosses.py [묶음 ...]"""
import subprocess, sys, os
from concurrent.futures import ThreadPoolExecutor
ROOT=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); OUT=ROOT+'/art/bosses'
B = {
 'city':    'a HUGE obese bloated zombie brute, a former civilian in a stretched torn tank top, massive belly, enormous fists',
 'subway':  'a tall hulking subway maintenance worker zombie in an orange hi-vis work vest and hard hat, dragging a long steel crowbar',
 'factory': 'a massive electrocuted welder zombie, welding mask fused to the face, sparks and small blue electric arcs crackling on its body, leather apron',
 'forest':  'a giant swamp zombie made of mud and rotting wood, covered in moss and vines, roots growing from its shoulders, glowing eyes',
 'base':    'a heavy armored soldier zombie in bulky bomb-disposal style armor and a cracked helmet visor, huge armored shoulders',
 'lab':     'the origin mutant zombie: a towering pale mutated creature with glowing teal veins, an exposed brain, and several tentacles sprouting from its back',
 # M11 (지시 #157) — 구역 35·40·45·50·55·60
 'school':  'a giant hulking P.E. teacher zombie in a torn tracksuit with a whistle around the neck, swinging a dented steel baseball bat',
 'mart':    'a massive supermarket butcher zombie in a blood-stained white apron and rubber boots, holding a huge meat cleaver',
 'park':    'a giant amusement park mascot bear zombie, a huge torn brown bear costume ripped open with zombie flesh showing, one button eye hanging',
 'prison':  'a towering muscular prisoner zombie in a ripped orange jumpsuit, broken shackles and heavy chains hanging from both wrists, swinging the chains',
 'cruise':  'a giant cruise ship captain zombie in a torn white captain uniform and cap, covered in barnacles and seaweed, dragging a rusty anchor',
 'nuclear': 'the final boss: a towering radioactive giant zombie, lumpy mutated body glowing toxic GREEN from cracks in its skin, glowing green eyes, remains of a yellow radiation suit',
}
TPL=("Pixel art game SPRITE SHEET of a BOSS ZOMBIE: {d}, glowing red eyes, menacing and much bulkier than a normal zombie. Exactly 4 frames in ONE horizontal row, "
     "evenly spaced with clear gaps, identical character design, size and scale in every frame, full body, pure side view FACING RIGHT. "
     "Frame 1-2: heavy stomping WALK (legs alternate). Frame 3: CHARGE WIND-UP (crouches low, leans back, ready to dash). Frame 4: CHARGE (lunging forward fast, body leaning far forward, arms out). "
     "Feet on the same baseline. Match exactly the pixel art style, outline, shading and muted palette of the reference zombie sprite sheet, but a different, bigger character as described. "
     "No text, no labels, no frame borders, no ground shadows, no motion lines.")
def run(k):
    if os.path.exists(f'{OUT}/{k}.png') and '--force' not in sys.argv: return k,'skip'
    r=subprocess.run(['python3',ROOT+'/nanobanana/nanobanana.py',TPL.format(d=B[k]),'--ref',ROOT+'/art/zombies/city_civilian.png','--model','flash','--size','512px','--aspect','21:9','--transparent','--no-trim','--out',f'{OUT}/{k}.png'],capture_output=True,text=True)
    return k,[l for l in (r.stdout+r.stderr).splitlines() if '저장' in l or '오류' in l][-1:]
keys=[k for k in B if len([a for a in sys.argv[1:] if not a.startswith('--')])==0 or k in sys.argv[1:]]
with ThreadPoolExecutor(3) as ex:
    for k,msg in ex.map(run,keys): print(k,msg)
