"""Play 스토어 그래픽 (지시 #210) — 앱 아이콘 512×512 · 그래픽 이미지 1024×500.
아이콘 = ios/AppIcon-1024.png 를 줄인 것(앱 아이콘과 같은 그림).
그래픽 이미지 = 시작 화면 키 아트(art/title/title_bg.png)의 가로 띠 + 게임 시작 화면과 같은 로고(흰 글자·검은 테·붉은 칼자국·금색 영문).
쓰는 법: python art/store/make_store_art.py  → art/store/icon-512.png, art/store/feature-1024x500.png
"""
import os
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'art', 'store')
FONT_B = r'C:\Windows\Fonts\malgunbd.ttf'

# 아이콘
icon = Image.open(os.path.join(ROOT, 'ios', 'AppIcon-1024.png')).convert('RGB').resize((512, 512), Image.LANCZOS)
icon.save(os.path.join(OUT, 'icon-512.png'), optimize=True)

# 그래픽 이미지 — 키 아트에서 불타는 도시·좀비 떼·주인공이 다 들어가는 띠를 잘라 1024 폭으로
src = Image.open(os.path.join(ROOT, 'art', 'title', 'title_bg.png')).convert('RGB')
W, H = 1024, 500
k = W / src.width
band_h = round(H / k)
top = int(os.environ.get('BAND_TOP', 790))
fg = src.crop((0, top, src.width, top + band_h)).resize((W, H), Image.LANCZOS)

# 오른쪽을 어둡게 — 로고가 읽히게(주인공은 가운데라 로고는 오른쪽 좀비 떼 위에)
shade = Image.new('L', (W, H))
sd = ImageDraw.Draw(shade)
for x in range(W):
    a = max(0, min(1, (x - 560) / 380))
    sd.line([(x, 0), (x, H)], fill=int(205 * a))
fg = Image.composite(Image.new('RGB', (W, H), (4, 4, 6)), fg, shade)

# 붉은 칼자국 두 줄(빛 번짐 + 선)
glow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
gd = ImageDraw.Draw(glow)
for (x0, y0, x1, y1, w) in [(580, 320, 975, 120, 11), (610, 352, 950, 172, 6)]:
    gd.line([(x0, y0), (x1, y1)], fill=(214, 40, 30, 150), width=w * 3)
glow = glow.filter(ImageFilter.GaussianBlur(8))
img = fg.convert('RGBA')
img.alpha_composite(glow)
ld = ImageDraw.Draw(glow)
lines = Image.new('RGBA', (W, H), (0, 0, 0, 0))
ldd = ImageDraw.Draw(lines)
for (x0, y0, x1, y1, w) in [(580, 320, 975, 120, 11), (610, 352, 950, 172, 6)]:
    ldd.line([(x0, y0), (x1, y1)], fill=(232, 58, 40, 235), width=w)
img.alpha_composite(lines)

# 로고 글자
d = ImageDraw.Draw(img)
f1 = ImageFont.truetype(FONT_B, 76)
f2 = ImageFont.truetype(FONT_B, 27)
def word(txt, xy, font):
    d.text(xy, txt, font=font, fill=(255, 255, 255), stroke_width=9, stroke_fill=(8, 8, 10))
word('아포칼립스', (584, 104), f1)
word('서바이버', (680, 202), f1)
d.text((680, 312), 'Apocalypse Survivor', font=f2, fill=(232, 190, 92), stroke_width=4, stroke_fill=(8, 8, 10))
img.convert('RGB').save(os.path.join(OUT, 'feature-1024x500.png'), optimize=True)
print('ok', icon.size, img.size)
