# 產生背景紋路（大理石、潑墨、刺繡線紋、宣紙金箔）與選項預覽圖
import math, os, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')


def hexrgb(h):
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], float)


def noise(w, h, cell, seed, octaves=4):
    """平滑雜訊 0~1：多層不同粗細的隨機格子放大後疊加"""
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w)); amp = 1.0; tot = 0.0
    for o in range(octaves):
        c = max(2, int(cell / 2 ** o))
        g = rng.random((h // c + 3, w // c + 3))
        im = Image.fromarray((g * 255).astype('uint8')).resize((w + 2 * c, h + 2 * c), Image.BICUBIC)
        out += np.asarray(im).astype(float)[c:c + h, c:c + w] / 255 * amp
        tot += amp; amp *= 0.5
    return out / tot


def marble(w, h, base, cloud, vein, seed, vein_amt=0.9, cloud_amt=0.5):
    n = noise(w, h, 220, seed); n2 = noise(w, h, 90, seed + 1); warp = noise(w, h, 300, seed + 2)
    xx, yy = np.meshgrid(np.arange(w), np.arange(h))

    def veins(freq, sharp, sd):
        t = (xx * 0.6 + yy * 0.8) / freq + (noise(w, h, 160, sd) - 0.5) * 9 + (warp - 0.5) * 6
        return (1 - np.abs(np.sin(t))) ** sharp

    v = np.clip(veins(95, 26, seed + 3) + 0.6 * veins(55, 40, seed + 4) * (n2 > 0.5), 0, 1)
    img = base[None, None] * (1 - cloud_amt * n[..., None]) + cloud[None, None] * cloud_amt * n[..., None]
    return img * (1 - vein_amt * v[..., None]) + vein[None, None] * vein_amt * v[..., None]


def ink(w, h, paper, inkc, seed, amount=0.55):
    rng = random.Random(seed)
    grain = noise(w, h, 6, seed + 9, 2)
    img = np.ones((h, w, 3)) * paper * (0.985 + 0.03 * grain[..., None])
    m = Image.new('L', (w, h), 0); d = ImageDraw.Draw(m)
    for _ in range(max(3, h // 420)):          # 幾團大的墨暈＋飛濺的小點，都靠左右兩側
        cx = rng.choice([rng.uniform(-40, w * .3), rng.uniform(w * .7, w + 40)]); cy = rng.uniform(0, h)
        for _ in range(26):
            a, r, rad = rng.uniform(0, 6.28), rng.gauss(0, 70), rng.uniform(14, 70)
            x, y = cx + r * math.cos(a), cy + r * math.sin(a) * 1.4
            d.ellipse((x - rad, y - rad, x + rad, y + rad), fill=rng.randint(60, 200))
        for _ in range(40):
            a, r, rad = rng.uniform(0, 6.28), abs(rng.gauss(120, 90)), rng.uniform(1, 5)
            x, y = cx + r * math.cos(a), cy + r * math.sin(a)
            d.ellipse((x - rad, y - rad, x + rad, y + rad), fill=rng.randint(120, 230))
    soft = np.asarray(m.filter(ImageFilter.GaussianBlur(16))).astype(float) / 255
    hard = np.asarray(m.filter(ImageFilter.GaussianBlur(2))).astype(float) / 255
    wash = np.clip(soft * 1.1 * (0.5 + noise(w, h, 60, seed + 5)) + 0.25 * hard, 0, 1) * amount
    return img * (1 - wash[..., None]) + inkc[None, None] * wash[..., None]


def stitched(w, h, base, thread, kind, alpha=0.5, S=2):
    """刺繡線紋：海水紋(wave) / 雲紋(cloud)，線條做成一針一針的虛線"""
    W, Hh = w * S, h * S
    m = Image.new('L', (W, Hh), 0); d = ImageDraw.Draw(m)

    def arc(cx, cy, r, a0, a1, wd=3):
        n = max(6, int(r * abs(a1 - a0) / 9))
        for i in range(0, n, 2):
            t0 = a0 + (a1 - a0) * i / n; t1 = a0 + (a1 - a0) * (i + 0.8) / n
            d.line((cx + r * math.cos(t0), cy + r * math.sin(t0), cx + r * math.cos(t1), cy + r * math.sin(t1)), fill=255, width=wd)

    if kind == 'wave':
        R = 44
        for row in range(-1, Hh // (R // 2) + 2):
            for col in range(-1, W // (2 * R) + 2):
                cx = col * 2 * R + (R if row % 2 else 0); cy = row * R // 2 + R
                for k in (1, 0.72, 0.44):
                    arc(cx, cy, R * k, math.pi, 2 * math.pi)
    else:
        rng = random.Random(4); st = 120
        for row in range(Hh // st + 2):
            for col in range(W // (st * 2) + 2):
                cx = col * st * 2 + (st if row % 2 else 0) + rng.uniform(-10, 10); cy = row * st + 40
                r = 26
                arc(cx - r, cy, r, math.pi * .5, math.pi * 2.2); arc(cx + r, cy, r, math.pi * .8, math.pi * 2.5)
                arc(cx, cy - r * .9, r * 1.1, math.pi * .9, math.pi * 2.1)
                arc(cx - r * 2.6, cy + r * .7, r * 1.6, math.pi * 1.5, math.pi * 2); arc(cx + r * 2.6, cy + r * .7, r * 1.6, math.pi, math.pi * 1.5)
    m = np.asarray(m.resize((w, h), Image.LANCZOS)).astype(float) / 255 * alpha
    g = noise(w, h, 5, 3, 2)
    img = np.ones((h, w, 3)) * base * (0.975 + 0.05 * g[..., None])
    return img * (1 - m[..., None]) + thread[None, None] * m[..., None]


def paper_gold(w, h, base, gold, seed):
    rng = random.Random(seed)
    g = noise(w, h, 4, seed, 2); c = noise(w, h, 180, seed + 1)
    img = np.ones((h, w, 3)) * base * (0.96 + 0.05 * g[..., None] + 0.03 * c[..., None])
    m = Image.new('L', (w * 2, h * 2), 0); d = ImageDraw.Draw(m)
    for _ in range(int(w * h / 2600)):
        x, y, r = rng.uniform(0, w * 2), rng.uniform(0, h * 2), rng.choice([2, 3, 4, 6, 9, 14])
        d.polygon([(x + r * rng.uniform(.4, 1) * math.cos(a), y + r * rng.uniform(.4, 1) * math.sin(a))
                   for a in np.linspace(0, 6.28, 6)[:-1]], fill=rng.randint(150, 255))
    for _ in range(int(w * h / 9000)):   # 紙纖維
        x, y, a, ln = rng.uniform(0, w * 2), rng.uniform(0, h * 2), rng.uniform(0, 3.14), rng.uniform(20, 60)
        d.line((x, y, x + ln * math.cos(a), y + ln * math.sin(a)), fill=70, width=1)
    m = np.asarray(m.resize((w, h), Image.LANCZOS)).astype(float) / 255
    return img * (1 - m[..., None]) + gold[None, None] * m[..., None]


# 名稱: (產生函式, 是否深色, 文字色, 強調色)
TEX = {
    'A 白大理石・金脈': (lambda w, h: marble(w, h, hexrgb('#FBFAF7'), hexrgb('#E6E2DC'), hexrgb('#C9A45C'), 11), False, '#3E3A36', '#A3262A'),
    'B 灰白大理石': (lambda w, h: marble(w, h, hexrgb('#F7F7F6'), hexrgb('#DADBDD'), hexrgb('#9A9CA0'), 23, 0.6, 0.6), False, '#33363B', '#A3262A'),
    'C 青花潑墨': (lambda w, h: ink(w, h, hexrgb('#FAFAF7'), hexrgb('#2A4E9B'), 5), False, '#22335A', '#1F3F8F'),
    'D 水墨暈染': (lambda w, h: ink(w, h, hexrgb('#F8F6F1'), hexrgb('#3A3A3C'), 8, 0.42), False, '#2E2C2A', '#A3262A'),
    'E 朱紅潑墨': (lambda w, h: ink(w, h, hexrgb('#FBF6EF'), hexrgb('#B8322E'), 12, 0.5), False, '#4A2B26', '#A3262A'),
    'F 宣紙・金箔': (lambda w, h: paper_gold(w, h, hexrgb('#FAF5EA'), hexrgb('#C9A45C'), 2), False, '#4A3F36', '#A3262A'),
    'G 刺繡海水紋・象牙': (lambda w, h: stitched(w, h, hexrgb('#FAF6EE'), hexrgb('#C9A45C'), 'wave', 0.55), False, '#4A3F36', '#A3262A'),
    'H 刺繡雲紋・青瓷': (lambda w, h: stitched(w, h, hexrgb('#EAF0F5'), hexrgb('#5C7DB8'), 'cloud', 0.55), False, '#26364F', '#1F3F8F'),
    'I 刺繡海水紋・喜氣紅': (lambda w, h: stitched(w, h, hexrgb('#A8262B'), hexrgb('#F0D08A'), 'wave', 0.5), True, '#FBEBD0', '#F0D08A'),
    'J 午夜藍大理石・金脈': (lambda w, h: marble(w, h, hexrgb('#1E2A47'), hexrgb('#2C3C63'), hexrgb('#D9B66E'), 31, 0.85, 0.7), True, '#EDE6D6', '#E0BE7A'),
}


def font(sz, bold=True):
    f = ImageFont.truetype('C:/Windows/Fonts/NotoSerifTC-VF.ttf', sz)
    f.set_variation_by_name('Bold' if bold else 'Regular')
    return f


def preview():
    src = np.asarray(Image.open(os.path.join(ROOT, 'work/video/sit_src.png')).convert('RGB').resize((300, 400), Image.LANCZOS)).astype(float)
    k = np.clip((src.min(axis=2) - 226) / 18, 0, 1)[..., None]
    W, H, pad = 330, 610, 18
    sheet = Image.new('RGB', (5 * W + 6 * pad, 2 * H + 3 * pad), '#777777')
    for n, (name, (fn, dark, fg, ac)) in enumerate(TEX.items()):
        tex = fn(W, H)
        t = tex[100:500, 15:315].copy()
        if dark:   # 深色底：近似去背
            tex[100:500, 15:315] = src * (1 - k) + t * k
        else:      # 淺色底：影片的白背景用「色彩增值」，紋路會透出來
            tex[100:500, 15:315] = np.minimum(src + k * (255 - src), 255) * t / 255
        card = Image.fromarray(tex.clip(0, 255).astype('uint8')); d = ImageDraw.Draw(card)
        d.text((W / 2, 52), '我們結婚啦', font=font(30), fill=ac, anchor='mm')
        d.text((W / 2, 86), '蕭苰栯 ♥ 洪韻雯', font=font(17), fill=fg, anchor='mm')
        d.text((W / 2, 528), '遇見了對的人，就想把往後的每一天', font=font(14, False), fill=fg, anchor='mm')
        d.rounded_rectangle((70, 550, W - 70, 588), 19, fill=ac)
        d.text((W / 2, 569), '送出回覆', font=font(15), fill='#3A1A1A' if dark else '#FFFFFF', anchor='mm')
        tw = d.textlength(name, font=font(15))
        d.rounded_rectangle((6, 6, 18 + tw, 30), 6, fill='#000000')
        d.text((12, 18), name, font=font(15), fill='#FFFFFF', anchor='lm')
        sheet.paste(card, (pad + (n % 5) * (W + pad), pad + (n // 5) * (H + pad)))
    sheet.save(os.path.join(ROOT, 'work/texture-options.jpg'), quality=90)
    print('ok')


if __name__ == '__main__':
    preview()
