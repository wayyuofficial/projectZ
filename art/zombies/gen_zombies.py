# -*- coding: utf-8 -*-
"""좀비 시트 생성(나노바나나 flash 512px, 21:9, 한 줄 6프레임: 걷기 4 · 공격 2, 오른쪽을 본다). 첫 장 city_civilian 을 ref 로 화풍 통일.
   있는 파일은 건너뛴다(--force 로 다시). M9 1.1 · M11 2.3(지시 #157). 쓰는 법: python art/zombies/gen_zombies.py [이름 ...]"""
import subprocess, sys, os
from concurrent.futures import ThreadPoolExecutor
ROOT=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); OUT=ROOT+'/art/zombies'
Z = {
 'city_office':    'an infected office worker zombie in a torn white shirt, loose necktie and dark slacks, pale grey-green skin',
 'city_police':    'an infected police officer zombie in a torn dark navy police uniform with a cap and badge, grey-green skin',
 'subway_commuter':'an infected commuter zombie in a long beige trench coat with a shoulder bag, grey-green skin',
 'subway_staff':   'an infected subway station staff zombie in a teal-green transit uniform vest and cap, grey-green skin',
 'subway_homeless':'an infected homeless zombie in layered ragged brown blankets and a beanie, long beard, grey-green skin, both arms visibly attached at the shoulders in every frame, in the attack frames the arms raise from the shoulders without hiding under the blanket',   # M15 (분석 B3): 공격 프레임의 손이 떠 보였다
 'factory_worker': 'an infected factory worker zombie in stained orange overalls and a yellow hard hat, grey-green skin',
 'factory_welder': 'an infected welder zombie wearing a dark welding mask pushed up, leather apron and heavy gloves, grey-green skin',
 'factory_hazmat': 'an infected chemical worker zombie in a torn yellow hazmat suit with a cracked gas mask',
 'forest_farmer':  'an infected farmer zombie in a straw hat, plaid shirt and denim overalls, grey-green skin',
 'forest_drowned': 'a bloated drowned swamp zombie covered in mud, algae and hanging moss, dark green-blue skin',
 'base_soldier':   'an infected soldier zombie in torn olive camouflage fatigues, helmet and tactical vest, grey-green skin',
 'base_patient':   'an infected hospital patient zombie in a torn pale blue hospital gown with bandages, barefoot, grey-green skin',
 'base_medic':     'an infected field medic zombie in a white protective suit with a red cross armband and face mask',
 'lab_scientist':  'an infected scientist zombie in a torn bloody white lab coat, glasses and ID badge, grey-green skin',
 'lab_subject':    'a mutated lab test-subject zombie, bald head, pale skin with glowing teal veins all over, numbered grey jumpsuit, BOTH arms equally long and thin with long claws, the same in every frame, both arms visibly connected to the shoulders in every frame including the raised attack frame (no floating hands)',   # M15 (분석 B3)
 # M11 (지시 #157) — 구역 31~60
 'school_student': 'an infected high school student zombie in a torn navy school uniform blazer and skirt-or-slacks, a backpack strap on one shoulder, grey-green skin',
 'school_teacher': 'an infected teacher zombie in a torn brown cardigan, collared shirt and glasses, holding nothing, grey-green skin',
 'school_cook':    'an infected school cafeteria cook zombie in a white apron, white cook cap and rubber gloves, grey-green skin',
 'mart_clerk':     'an infected supermarket clerk zombie in a bright green store vest over a white shirt with a name tag, grey-green skin',
 'mart_shopper':   'an infected shopper zombie in a puffy winter jacket, clutching a torn plastic shopping bag, grey-green skin',
 'mart_guard':     'an infected supermarket security guard zombie in a black security uniform and cap, grey-green skin',
 'park_mascot':    'an infected amusement park mascot zombie in a dirty torn pink bunny costume with the head mask half off, showing a zombie face',
 'park_clown':     'an infected clown zombie with smeared white face paint, red nose, colorful baggy polka-dot suit and big shoes',
 'park_staff':     'an infected amusement park ride operator zombie in a striped red-white uniform shirt and visor cap, grey-green skin',
 'prison_inmate':  'an infected prisoner zombie in a torn bright orange prison jumpsuit, shaved head, tattoos, grey-green skin',
 'prison_guard':   'an infected prison guard zombie in a grey-blue correctional officer uniform with a baton holster, grey-green skin',
 'prison_riot':    'an infected riot police zombie in black riot armor with a cracked helmet visor, grey-green skin',
 'cruise_crew':    'an infected cruise ship crew zombie in a white sailor uniform with navy trim, grey-green skin',
 'cruise_tourist': 'an infected tourist zombie in a bright floral Hawaiian shirt, shorts, sunglasses on the head and a camera strap, grey-green skin',
 'cruise_chef':    'an infected ship chef zombie in a stained white chef jacket and tall chef hat, grey-green skin',
 'nuclear_worker': 'an infected nuclear plant worker zombie in a torn YELLOW radiation protection suit with a black radiation trefoil symbol, hood down, grey-green skin',
 'nuclear_mutant': 'a radioactive mutant zombie with bald head, lumpy skin and glowing toxic GREEN veins and glowing green eyes instead of red, torn grey clothes',
 'nuclear_guard':  'an infected nuclear plant security guard zombie in a dark green security uniform with a gas mask hanging on the neck, grey-green skin',
 # M29 (지시 #194) — 구역 61~70 지하 벙커
 'bunker_marine':  'an infected special forces soldier zombie in black tactical gear, torn balaclava and night-vision goggles pushed up, grey-green skin',
 'bunker_officer': 'an infected military officer zombie in a torn grey dress uniform with medals and a peaked cap, grey-green skin',
 'bunker_tech':    'an infected bunker technician zombie in a dirty grey jumpsuit with a tool belt and a headset, grey-green skin',
 'core_host':      'a zombie fused with dark red organic flesh growths and pulsing veins over its torn clothes, glowing red cracks in the skin, BOTH arms visibly attached at the shoulders in every frame',
 'core_researcher':'an infected chief researcher zombie in a long torn black lab coat stained with red, a cracked respirator mask, grey-green skin',
 'core_crawler':   'a hunched mutated zombie with an elongated spine and bony spikes on its back, pale grey skin with red veins, walking on two legs bent low, both arms long and clawed',
}
TPL=("Pixel art game SPRITE SHEET of a ZOMBIE: {d}, glowing red eyes. Exactly 6 frames in ONE horizontal row, evenly spaced with clear gaps, "
     "identical character design, size and scale in every frame, full body, pure side view FACING RIGHT. Frames 1-4: a slow shambling WALK CYCLE "
     "(legs alternate, arms reaching forward). Frames 5-6: ATTACK (frame 5 raises arms back, frame 6 lunges forward clawing). Feet on the same baseline. "
     "Match exactly the pixel art style, proportions, outline and muted palette of the reference zombie sprite sheet (same body size and head size), "
     "but a different character as described. No text, no labels, no frame borders, no ground shadows.")
def run(k):
    if os.path.exists(f'{OUT}/{k}.png') and '--force' not in sys.argv: return k,'skip'
    r=subprocess.run([sys.executable,(os.path.join('D:'+os.sep,'nanobanana','nanobanana.py') if os.name=='nt' else ROOT+'/nanobanana/nanobanana.py'),TPL.format(d=Z[k]),'--ref',OUT+'/city_civilian.png','--model','flash','--size','512px','--aspect','21:9','--transparent','--no-trim','--out',f'{OUT}/{k}.png'],capture_output=True,text=True,encoding='utf-8',errors='replace')
    return k,(r.stdout+r.stderr).strip().splitlines()[-1][:120]
keys=[k for k in Z if len(sys.argv)<2 or k in sys.argv[1:]]
with ThreadPoolExecutor(4) as ex:
    for k,msg in ex.map(run,keys): print(k,msg)
