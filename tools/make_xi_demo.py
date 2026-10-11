# 「囍」字的 10 種刺繡樣式 demo
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_embroidery_demo import embroider, shadowed, cloud_mask, peony, erode, rgb, PALETTES, ROOT  # noqa: E402

T = 720   # 每格 2 倍繪製，輸出 360
P = PALETTES[0]
GOLD, GOLD_L, GOLD_D = P['gold'], P['gold_l'], P['gold_d']
RED, RED_D, CREAM, TEAL = rgb('#B01218'), rgb('#7A0A10'), rgb('#F7EBD3'), rgb('#1F8A8A')
FONTS = {
    'serif': ('C:/Windows/Fonts/NotoSerifTC-VF.ttf', 'Bold'),
    'sans': ('C:/Windows/Fonts/msjhbd.ttc', None),
    'kai': ('C:/Windows/Fonts/kaiu.ttf', None),
}


def xi_mask(size, font='serif', fat=0, canvas=T):
    path, var = FONTS[font]
    f = ImageFont.truetype(path, size)
    if var:
        f.set_variation_by_name(var)
    m = Image.new('L', (canvas, canvas), 0)
    ImageDraw.Draw(m).text((canvas / 2, canvas / 2 + size * 0.04), '囍', font=f, fill=255, anchor='mm')
    if fat:   # 稍微加粗、把轉角磨圓（加太多筆畫會黏在一起）
        m = m.filter(ImageFilter.MaxFilter(2 * fat + 1)).filter(ImageFilter.GaussianBlur(2.2)).point(lambda v: 255 if v > 128 else 0)
    return m


def shape(kind, r, canvas=T):
    m = Image.new('L', (canvas, canvas), 0); d = ImageDraw.Draw(m); c = canvas / 2
    if kind == 'circle':
        d.ellipse((c - r, c - r, c + r, c + r), fill=255)
    elif kind == 'square':
        d.rounded_rectangle((c - r, c - r, c + r, c + r), r * 0.16, fill=255)
    elif kind == 'diamond':
        d.polygon([(c, c - r), (c + r, c), (c, c + r), (c - r, c)], fill=255)
    elif kind == 'octagon':
        d.polygon([(c + r * math.cos(math.pi / 8 + i * math.pi / 4), c + r * math.sin(math.pi / 8 + i * math.pi / 4)) for i in range(8)], fill=255)
    elif kind == 'scallop':
        d.ellipse((c - r * .9, c - r * .9, c + r * .9, c + r * .9), fill=255)
        for i in range(16):
            a = i * math.pi / 8
            x, y = c + r * .9 * math.cos(a), c + r * .9 * math.sin(a)
            d.ellipse((x - r * .2, y - r * .2, x + r * .2, y + r * .2), fill=255)
    return m


def ring(kind, r, wd):
    return ImageChops.subtract(shape(kind, r), shape(kind, r - wd))


def tile():
    yy, xx = np.mgrid[0:T, 0:T]
    t = np.clip(np.hypot(xx - T / 2, yy - T / 2) / (T * 0.75), 0, 1)[..., None]
    a = np.array(rgb('#A80F16'), float) * (1 - t) + np.array(rgb('#6A0408'), float) * t
    return Image.fromarray(a.astype('uint8')).convert('RGBA')


def put(im, layer, sh=True, at=(0, 0)):
    if sh:
        lay, pad = shadowed(layer, (5, 8), 8, 0.45)
        im.alpha_composite(lay, (at[0] - pad, at[1] - pad))
    else:
        im.alpha_composite(layer, at)


def glow(im, r, col=(255, 200, 120), a=70):
    g = Image.new('L', (T, T), 0)
    ImageDraw.Draw(g).ellipse((T / 2 - r, T / 2 - r, T / 2 + r, T / 2 + r), fill=a)
    lay = Image.new('RGBA', (T, T), col + (0,)); lay.putalpha(g.filter(ImageFilter.GaussianBlur(40)))
    im.alpha_composite(lay)


def d1():   # 圓章・粗圓雙線字（最接近參考範本的感覺）
    im = tile(); glow(im, 300)
    put(im, embroider(shape('circle', 250), [RED_D, rgb('#8E0C12')], 60, GOLD, 6, 1))
    put(im, embroider(xi_mask(350, 'sans', 1), [GOLD_L, RED_D], 6, GOLD_D, 3, 2))
    return im, '1 圓章・粗圓雙線字'


def d2():   # 金線圓框・細緻明體
    im = tile()
    put(im, embroider(ring('circle', 270, 22), [GOLD_L, GOLD, GOLD_L], 6, GOLD_D, 4, 3))
    put(im, embroider(ring('circle', 232, 5), [GOLD_L], 3, None, 0, 4), False)
    put(im, embroider(xi_mask(330, 'serif'), [GOLD_L, GOLD], 5, GOLD_D, 3, 5))
    return im, '2 金線圓框・明體'


def d3():   # 金盤紅字
    im = tile(); glow(im, 300)
    put(im, embroider(shape('circle', 255), [GOLD_L, GOLD, GOLD_L, GOLD], 22, GOLD_D, 6, 6))
    put(im, embroider(xi_mask(340, 'sans', 1), [RED, RED_D], 7, rgb('#5A0408'), 3, 7))
    return im, '3 金盤紅字'


def d4():   # 方形印章・楷書
    im = tile()
    put(im, embroider(shape('square', 240), [GOLD_L, RED_D, RED, rgb('#9A0E14')], 12, GOLD, 8, 8))
    put(im, embroider(xi_mask(360, 'kai', 3), [GOLD_L, GOLD], 6, GOLD_D, 3, 9))
    return im, '4 方印・楷書'


def d5():   # 斗方（菱形春聯）
    im = tile()
    put(im, embroider(shape('diamond', 320), [GOLD_L, RED, RED_D], 12, GOLD, 8, 10))
    put(im, embroider(ring('diamond', 262, 5), [GOLD_L], 3, None, 0, 11), False)
    put(im, embroider(xi_mask(280, 'serif', 2), [GOLD_L, GOLD], 5, GOLD_D, 3, 12))
    return im, '5 斗方・菱形'


def d6():   # 八角窗花
    im = tile()
    put(im, embroider(ring('octagon', 300, 26), [GOLD_L, GOLD, GOLD_L], 7, GOLD_D, 4, 13))
    put(im, embroider(ring('octagon', 254, 8), [TEAL, rgb('#7CC6B4')], 4, GOLD, 2, 14))
    put(im, embroider(xi_mask(310, 'sans', 4), [GOLD_L, GOLD, GOLD_L], 6, GOLD_D, 4, 15))
    return im, '6 八角窗花'


def d7():   # 祥雲環繞
    im = tile()
    for flip, x, y in ((False, -10, 500), (True, 390, 500)):
        put(im, embroider(cloud_mask((340, 180), flip), P['cloud'], 12, GOLD, 5, 16 + flip), True, (x, y))
    put(im, embroider(cloud_mask((200, 105), True), P['cloud'], 8, GOLD, 5, 18), True, (10, 40))
    put(im, embroider(cloud_mask((200, 105), False), P['cloud'], 8, GOLD, 5, 19), True, (510, 40))
    put(im, embroider(xi_mask(330, 'serif', 2), [GOLD_L, GOLD], 6, GOLD_D, 4, 20), True, (0, -40))
    return im, '7 祥雲環繞'


def d8():   # 牡丹托底
    im = tile()
    pe = peony(105, P, 3)
    put(im, pe, False, (T // 2 - pe.width // 2 - 150, 330))
    pe2 = peony(105, P, 9)
    put(im, pe2, False, (T // 2 - pe2.width // 2 + 150, 330))
    put(im, embroider(xi_mask(330, 'sans', 1, T), [GOLD_L, GOLD], 6, GOLD_D, 3, 21), True, (0, -80))
    return im, '8 牡丹托底'


def d9():   # 彩線漸層字
    im = tile(); glow(im, 280)
    put(im, embroider(xi_mask(440, 'sans', 2), [CREAM, rgb('#E2572B'), TEAL], 5, GOLD, 4, 22))
    return im, '9 彩色繡線字'


def d10():  # 花邊金盤・鏤空字
    im = tile(); glow(im, 300)
    disc = ImageChops.subtract(shape('scallop', 270), xi_mask(330, 'sans', 1))
    put(im, embroider(disc, [GOLD_L, GOLD, GOLD_L, GOLD], 16, GOLD_D, 5, 23))
    return im, '10 花邊金盤・鏤空'


if __name__ == '__main__':
    pad, lab = 16, 44
    S = T // 2
    sheet = Image.new('RGB', (5 * S + 6 * pad, 2 * (S + lab) + 3 * pad), '#2B2B2B')
    d = ImageDraw.Draw(sheet)
    f = ImageFont.truetype(FONTS['serif'][0], 20); f.set_variation_by_name('Bold')
    for i, fn in enumerate((d1, d2, d3, d4, d5, d6, d7, d8, d9, d10)):
        im, name = fn()
        x = pad + (i % 5) * (S + pad); y = pad + (i // 5) * (S + lab + pad)
        sheet.paste(im.convert('RGB').resize((S, S), Image.LANCZOS), (x, y))
        d.text((x + S / 2, y + S + lab / 2), name, font=f, fill='#FFFFFF', anchor='mm')
        print('done', i + 1)
    sheet.save(os.path.join(ROOT, 'work', 'xi-demos.jpg'), quality=92)
