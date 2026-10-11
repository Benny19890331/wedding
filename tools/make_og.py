# 產生 LINE / Facebook 分享預覽圖（1200x630）與網站小圖示
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
P = lambda *a: os.path.join(ROOT, 'assets', *a)
BG, PAPER, TEA, INK, GOLD, GOLD_L, RED = (243, 235, 224), (251, 247, 240), (176, 141, 106), (92, 70, 52), (201, 164, 92), (234, 212, 160), (178, 46, 46)
SERIF = 'C:/Windows/Fonts/NotoSerifTC-VF.ttf'


def font(size, bold=True):
    f = ImageFont.truetype(SERIF, size)
    f.set_variation_by_name('Bold' if bold else 'Regular')
    return f


def arch(path, w, h):
    ph = Image.open(path).convert('RGB')
    sc = max(w / ph.width, h / ph.height)
    ph = ph.resize((round(ph.width * sc), round(ph.height * sc)), Image.LANCZOS)
    ph = ph.crop(((ph.width - w) // 2, 0, (ph.width - w) // 2 + w, h))
    m = Image.new('L', (w, h), 0)
    d = ImageDraw.Draw(m)
    d.ellipse((0, 0, w, w), fill=255)
    d.rectangle((0, w // 2, w, h), fill=255)
    return ph, m


im = Image.new('RGB', (1200, 630), BG)
d = ImageDraw.Draw(im)
d.rounded_rectangle((40, 40, 1160, 590), 36, fill=PAPER, outline=GOLD, width=5)
d.rounded_rectangle((58, 58, 1142, 572), 24, outline=GOLD_L, width=2)

# 左側：青花瓷禮服舉牌「我們結婚啦」的畫面
ph = Image.open(P('video', 'wink.jpg')).convert('RGB')
w, h = 430, 474
sc = w / ph.width
ph = ph.resize((w, round(ph.height * sc)), Image.LANCZOS).crop((0, 10, w, 10 + h))
m = Image.new('L', (w, h), 0)
ImageDraw.Draw(m).rounded_rectangle((0, 0, w, h), 22, fill=255)
d.rounded_rectangle((90 - 5, 78 - 5, 90 + w + 5, 78 + h + 5), 26, fill=GOLD)
im.paste(ph, (90, 78), m)

# 名字用內海字體（和網頁一致）；愛心用原本的字體畫
NAIKAI = os.path.join(ROOT, 'work', 'fonts-src', 'NaikaiFont-Regular.ttf')
nf = ImageFont.truetype(NAIKAI, 44) if os.path.exists(NAIKAI) else font(40)
d.text((835, 140), '蕭苰栯', font=nf, fill=INK, anchor='rm')
d.text((865, 140), '♥', font=font(34), fill=RED, anchor='mm')
d.text((895, 140), '洪韻雯', font=nf, fill=INK, anchor='lm')
d.line((720, 182, 1010, 182), fill=GOLD, width=3)
d.text((865, 250), '我們結婚啦', font=font(70), fill=RED, anchor='mm')
d.text((865, 330), '2026．11．06（五）', font=font(38, False), fill=INK, anchor='mm')
d.text((865, 385), '午宴・11:00 開始', font=font(32, False), fill=TEA, anchor='mm')
d.text((865, 440), '高雄日航酒店 三樓宴會廳', font=font(34), fill=INK, anchor='mm')
d.text((865, 515), '點開看喜帖・回覆出席 ›', font=font(26, False), fill=GOLD, anchor='mm')
im.save(P('og.jpg'), quality=88, optimize=True)

# 小圖示：紅底金色囍
fav = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
fd = ImageDraw.Draw(fav)
fd.ellipse((2, 2, 126, 126), fill=RED)
fd.text((64, 68), '囍', font=font(84), fill=GOLD_L, anchor='mm')
fav.resize((64, 64), Image.LANCZOS).save(P('favicon.png'))
print('ok')
