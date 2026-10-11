# 產生喜帖用的 3 張循環 GIF（囍字、日曆、乾杯）（奶茶白為主、金紅為輔）
# 用法：python tools/make_gifs.py
import math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT = os.path.join(ROOT, 'assets', 'gif')

S = 800          # 繪製尺寸（2 倍），輸出時縮成一半，邊緣較平滑
OUT_SIZE = 400
FPS = 20

BG = (243, 235, 224)
MILK = (232, 219, 201)
PAPER = (251, 247, 240)
TEA = (176, 141, 106)
INK = (92, 70, 52)
GOLD = (201, 164, 92)
GOLD_L = (234, 212, 160)
RED = (178, 46, 46)
RED_D = (140, 32, 34)

SERIF = 'C:/Windows/Fonts/NotoSerifTC-VF.ttf'
KAI = 'C:/Windows/Fonts/kaiu.ttf'


def font(size, bold=True, path=SERIF):
    f = ImageFont.truetype(path, size)
    if path == SERIF:
        try:
            f.set_variation_by_name('Bold' if bold else 'Regular')
        except Exception:
            pass
    return f


def ease_out(t):  return 1 - (1 - t) ** 3
def ease_in_out(t): return 3 * t * t - 2 * t * t * t
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def seg(t, a, b): return clamp((t - a) / (b - a))


def heart_poly(cx, cy, size, rot=0):
    pts = []
    for i in range(60):
        a = i / 60 * 2 * math.pi
        x = 16 * math.sin(a) ** 3
        y = -(13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a))
        x, y = x * size / 32, y * size / 32
        c, s = math.cos(rot), math.sin(rot)
        pts.append((cx + x * c - y * s, cy + x * s + y * c))
    return pts


def sparkle(d, cx, cy, r, color):
    """四角星"""
    w = r * 0.28
    d.polygon([(cx, cy - r), (cx + w, cy - w), (cx + r, cy), (cx + w, cy + w),
               (cx, cy + r), (cx - w, cy + w), (cx - r, cy), (cx - w, cy - w)], fill=color)


def with_alpha(img, a):
    img = img.copy()
    al = img.getchannel('A').point(lambda v: int(v * a))
    img.putalpha(al)
    return img


def text_center(d, xy, s, f, fill):
    d.text(xy, s, font=f, fill=fill, anchor='mm')


def save_gif(frames, name, photo=False, fps=FPS):
    small = [f.convert('RGB').resize((OUT_SIZE, OUT_SIZE), Image.LANCZOS) for f in frames]
    # 共用調色盤，避免閃爍
    step = max(1, len(small) // 8)
    sample = small[::step]
    strip = Image.new('RGB', (OUT_SIZE, OUT_SIZE * len(sample)))
    for i, im in enumerate(sample):
        strip.paste(im, (0, i * OUT_SIZE))
    pal = strip.quantize(colors=255 if photo else 96, method=Image.MEDIANCUT)
    # 把最接近底色的調色盤顏色校正成網頁底色，GIF 才不會有色差方框
    pv = pal.getpalette()[:768]
    idx = min(range(len(pv) // 3), key=lambda i: sum((pv[i * 3 + j] - BG[j]) ** 2 for j in range(3)))
    pv[idx * 3:idx * 3 + 3] = list(BG)
    pal.putpalette(pv)
    dither = Image.Dither.FLOYDSTEINBERG if photo else Image.Dither.NONE
    q = []
    for im in small:
        qi = im.quantize(palette=pal, dither=dither)
        # PIL 對應調色盤時會有些微誤差，底色像素直接指定成校正過的那一格
        src = np.asarray(im)
        arr = np.array(qi)
        arr[np.all(np.abs(src.astype(int) - BG) <= 2, axis=2)] = idx
        qi2 = Image.fromarray(arr, 'P')
        qi2.putpalette(pv)
        q.append(qi2)
    path = os.path.join(OUT, name)
    q[0].save(path, save_all=True, append_images=q[1:], duration=int(1000 / fps),
              loop=0, optimize=True, disposal=1)
    print(f'{name}: {len(q)} frames, {os.path.getsize(path) // 1024} KB')


# ---------------------------------------------------------------- 3. 金色囍字閃光
def gif_xi():
    N = 44
    base = Image.new('RGBA', (S, S), BG + (255,))
    d = ImageDraw.Draw(base)
    c, r = 400, 280
    d.ellipse((c - r, c - r, c + r, c + r), fill=RED)
    d.ellipse((c - r + 22, c - r + 22, c + r - 22, c + r - 22), outline=GOLD, width=8)
    d.ellipse((c - r + 40, c - r + 40, c + r - 40, c + r - 40), outline=GOLD_L, width=2)
    # 金色漸層囍字
    mask = Image.new('L', (S, S), 0)
    text_center(ImageDraw.Draw(mask), (c, c + 8), '囍', font(330), 255)
    grad = Image.new('RGBA', (S, S))
    gd = ImageDraw.Draw(grad)
    for y in range(S):
        k = y / S
        col = tuple(int(GOLD_L[j] * (1 - k) + GOLD[j] * k) for j in range(3))
        gd.line((0, y, S, y), fill=col + (255,))
    base.paste(grad, (0, 0), mask)
    circle = Image.new('L', (S, S), 0)
    ImageDraw.Draw(circle).ellipse((c - r, c - r, c + r, c + r), fill=255)
    stars = [(160, 170, 30, 0.0), (650, 190, 24, 0.3), (670, 610, 34, 0.55), (140, 630, 22, 0.8),
             (400, 70, 20, 0.15), (730, 420, 18, 0.65)]
    frames = []
    for i in range(N):
        t = i / N
        im = base.copy()
        p = seg(t, 0.05, 0.55)
        if 0 < p < 1:
            band = Image.new('L', (S, S), 0)
            bd = ImageDraw.Draw(band)
            x = -300 + p * (S + 600)
            bd.polygon([(x, 0), (x + 90, 0), (x + 90 - 500, S), (x - 500, S)], fill=150)
            band = band.filter(ImageFilter.GaussianBlur(18))
            band = ImageChops.multiply(band, circle)
            im.paste(Image.new('RGBA', (S, S), (255, 250, 235, 255)), (0, 0), band)
        dd = ImageDraw.Draw(im)
        for sx, sy, sr, ph in stars:
            a = 0.5 + 0.5 * math.sin(2 * math.pi * (t + ph))
            sparkle(dd, sx, sy, sr * (0.35 + 0.65 * a), GOLD)
        frames.append(im)
    save_gif(frames, '3-xi-shine.gif')


# ---------------------------------------------------------------- 5. 日曆翻到 11/6
def cal_page(num, final=False):
    w, h = 460, 500
    pg = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(pg)
    d.rounded_rectangle((0, 0, w - 1, h - 1), 26, fill=PAPER, outline=MILK, width=3)
    d.rounded_rectangle((0, 0, w - 1, 120), 26, fill=RED)
    d.rectangle((0, 90, w - 1, 120), fill=RED)
    text_center(d, (w / 2, 62), '2026 ・ 十一月', font(40), PAPER)
    text_center(d, (w / 2, 290), str(num), font(220), RED if final else INK)
    week = '日一二三四五六'[(num - 1) % 7]  # 2026/11/1 是星期日
    text_center(d, (w / 2, 440), f'星期{week}', font(36, False), TEA)
    return pg


def gif_calendar():
    per = 6
    flips = 5
    tail = 34
    N = flips * per + tail
    w, h = 460, 500
    ox, oy = (S - w) // 2, 170
    pages = {n: cal_page(n, n == 6) for n in range(1, 7)}
    frames = []
    for i in range(N):
        im = Image.new('RGBA', (S, S), BG + (255,))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((ox + 10, oy + 14, ox + w + 10, oy + h + 14), 26, fill=(0, 0, 0, 24))
        if i < flips * per:
            cur = i // per + 1
            p = ease_in_out((i % per) / per)
            im.alpha_composite(pages[cur + 1], (ox, oy))
            sh = max(1, int(h * (1 - p)))
            top = pages[cur].resize((w, sh), Image.BICUBIC)
            im.alpha_composite(top, (ox, oy))
        else:
            im.alpha_composite(pages[6], (ox, oy))
            q = ease_out(seg(i - flips * per, 0, 14))
            if q > 0:
                cx, cy, r = ox + w / 2, oy + 290, 150
                d.arc((cx - r, cy - r, cx + r, cy + r), -100, -100 + 360 * q, fill=RED, width=10)
            if i - flips * per > 12:
                k = seg(i - flips * per, 12, 22)
                d.polygon(heart_poly(ox + w - 40, oy + 170, 60 * ease_out(k), -0.3), fill=RED)
                text_center(d, (S / 2, 740), '記得來喝喜酒喔！', font(42), INK)
        # 日曆環
        for rx in (ox + 110, ox + w - 110):
            d.rounded_rectangle((rx - 12, oy - 34, rx + 12, oy + 30), 12, fill=GOLD)
        frames.append(im)
    save_gif(frames, '5-calendar-1106.gif')


# ---------------------------------------------------------------- 6. 乾杯
def glass_layer(bubble_t):
    g = Image.new('RGBA', (220, 520), (0, 0, 0, 0))
    d = ImageDraw.Draw(g)
    cx = 110
    bowl = [(cx - 70, 20), (cx + 70, 20), (cx + 58, 250), (cx + 20, 300), (cx - 20, 300), (cx - 58, 250)]
    liquid = [(cx - 64, 90), (cx + 64, 90), (cx + 55, 248), (cx + 18, 294), (cx - 18, 294), (cx - 55, 248)]
    d.polygon(liquid, fill=GOLD_L + (255,))
    for k in range(5):
        u = (bubble_t + k / 5) % 1
        by = 280 - u * 180
        bx = cx - 30 + (k * 17) % 60
        d.ellipse((bx - 6, by - 6, bx + 6, by + 6), outline=PAPER + (230,), width=3)
    d.line((cx - 64, 90, cx + 64, 90), fill=GOLD + (255,), width=4)
    d.polygon(bowl, outline=INK + (255,), width=6)
    d.line((cx - 44, 50, cx - 36, 200), fill=(255, 255, 255, 170), width=8)
    d.rectangle((cx - 6, 300, cx + 6, 470), fill=INK)
    d.ellipse((cx - 70, 460, cx + 70, 492), fill=INK)
    return g


def gif_cheers():
    N = 48
    frames = []
    for i in range(N):
        t = i / N
        im = Image.new('RGBA', (S, S), BG + (255,))
        d = ImageDraw.Draw(im)
        # 0→0.4 靠近、0.4→0.55 碰杯、0.55→1 回去
        if t < 0.4:
            a = ease_in_out(t / 0.4)
        elif t < 0.55:
            a = 1 - 0.08 * math.sin((t - 0.4) / 0.15 * math.pi * 2)
        else:
            a = 1 - ease_in_out((t - 0.55) / 0.45)
        ang = -10 + 28 * a      # 往外擺的角度收小，杯子才不會跑出畫面
        g = glass_layer(t)
        L = g.rotate(-ang, resample=Image.BICUBIC, expand=True, center=(110, 480))
        R = g.transpose(Image.FLIP_LEFT_RIGHT).rotate(ang, resample=Image.BICUBIC, expand=True, center=(110, 480))
        # 以杯底為支點放置
        im.alpha_composite(L, (int(250 - L.width / 2 - 6 * (1 - a)), int(680 - L.height + 60)))
        im.alpha_composite(R, (int(550 - R.width / 2 + 6 * (1 - a)), int(680 - R.height + 60)))
        q = seg(t, 0.4, 0.62)
        if 0 < q < 1:
            cx, cy = 400, 250
            for k in range(8):
                ang2 = k / 8 * 2 * math.pi
                r1 = 40 + 90 * ease_out(q)
                r2 = r1 + 40 * (1 - q)
                d.line((cx + r1 * math.cos(ang2), cy + r1 * math.sin(ang2),
                        cx + r2 * math.cos(ang2), cy + r2 * math.sin(ang2)), fill=GOLD, width=8)
            sparkle(d, cx, cy, 40 * (1 - q) + 10, RED)
        text_center(d, (400, 90), '乾 杯 ！', font(56), RED)
        d.line((140, 720, 660, 720), fill=MILK, width=4)
        frames.append(im)
    save_gif(frames, '6-cheers.gif')


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    gif_calendar()     # 囍字和乾杯已改成網頁內的向量動畫，不再用 GIF
