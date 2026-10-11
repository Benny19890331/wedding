# 刺繡風主視覺 demo：用程式畫出有繡線質感的祥雲、牡丹、海水紋、金線圓框，套 5 種配色
import math, os, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
W, H = 780, 1688           # 2 倍繪製，輸出 390x844
SERIF = 'C:/Windows/Fonts/NotoSerifTC-VF.ttf'


def rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def font(sz, bold=True):
    f = ImageFont.truetype(SERIF, sz)
    f.set_variation_by_name('Bold' if bold else 'Regular')
    return f


def erode(mask, px):
    px = int(px)
    while px > 0:               # 分段縮，避免一次用太大的濾鏡
        s = min(px, 6)
        mask = mask.filter(ImageFilter.MinFilter(2 * s + 1))
        px -= s
    return mask


def embroider(mask, bands, band_w=13, outline=None, outline_w=5, seed=0):
    """把一個形狀繡出來：外圈金線，往內一圈一圈換色，加上斜向繡線紋理與浮凸光影。回傳 RGBA。"""
    w, h = mask.size
    col = np.zeros((h, w, 3), float)
    theta = np.zeros((h, w))
    layers = ([outline] if outline else []) + list(bands)
    m = mask
    for k, c in enumerate(layers):
        a = np.asarray(m).astype(float)[..., None] / 255
        col = col * (1 - a) + np.array(c, float) * a
        theta = np.where(np.asarray(m) > 127, (k % 2) * 2 - 1, theta)
        m = erode(m, outline_w if (outline and k == 0) else band_w)
        if not m.getbbox():
            break
    yy, xx = np.mgrid[0:h, 0:w]
    rng = np.random.default_rng(abs(int(seed)))
    stitch = np.sin((xx + theta * yy) * 2 * math.pi / 5.0) * 0.09 + (rng.random((h, w)) - 0.5) * 0.08
    hm = np.asarray(mask.filter(ImageFilter.GaussianBlur(3))).astype(float) / 255
    lum = np.asarray(Image.fromarray(col.clip(0, 255).astype('uint8')).convert('L').filter(ImageFilter.GaussianBlur(1.5))).astype(float) / 255
    hgt = hm + lum * 0.35
    light = (np.roll(hgt, (2, 2), (0, 1)) - np.roll(hgt, (-2, -2), (0, 1))) * 0.9
    col = col * (1 + stitch[..., None] + light[..., None])
    out = Image.fromarray(col.clip(0, 255).astype('uint8')).convert('RGBA')
    out.putalpha(mask)
    return out


def shadowed(layer, off=(5, 8), blur=7, alpha=0.38):
    pad = 24
    base = Image.new('RGBA', (layer.width + pad * 2, layer.height + pad * 2), (0, 0, 0, 0))
    sh = Image.new('RGBA', base.size, (20, 0, 0, 0))
    a = Image.new('L', base.size, 0)
    a.paste(layer.getchannel('A'), (pad + off[0], pad + off[1]))
    sh.putalpha(a.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * alpha)))
    base.alpha_composite(sh)
    base.alpha_composite(layer, (pad, pad))
    return base, pad


# ------------------------------------------------------------ 圖案的形狀（黑白遮罩）
def cloud_mask(size, flip=False):
    """如意祥雲：三個圓瓣的雲頭＋往旁邊甩出去、越來越細的雲尾"""
    w, h = size
    m = Image.new('L', size, 0); d = ImageDraw.Draw(m)
    r = h * 0.27
    cx, cy = w * 0.30, h * 0.58
    for dx, dy, k in ((-0.9, 0.1, 1.0), (0.9, 0.1, 1.0), (0, -0.75, 1.12), (0, 0.25, 1.0)):
        rr = r * k
        d.ellipse((cx + dx * r - rr, cy + dy * r - rr, cx + dx * r + rr, cy + dy * r + rr), fill=255)
    for i in range(46):                         # 雲尾
        t = i / 45
        x = cx + r * 1.2 + t * (w - cx - r * 1.6)
        y = cy + r * 0.45 - math.sin(t * math.pi) * h * 0.20 + t * h * 0.06
        rr = r * (0.62 * (1 - t) ** 0.8 + 0.07)
        d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=255)
    # 尾端的小捲
    ex, ey = w - r * 0.75, cy + r * 0.45 + h * 0.06
    d.ellipse((ex - r * 0.42, ey - r * 0.9, ex + r * 0.42, ey - r * 0.06), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(2)).point(lambda v: 255 if v > 110 else 0)
    return m.transpose(Image.FLIP_LEFT_RIGHT) if flip else m


def petal_mask(size, ang):
    w, h = size
    m = Image.new('L', (w, h), 0); d = ImageDraw.Draw(m)
    d.ellipse((w * 0.18, h * 0.02, w * 0.82, h * 0.78), fill=255)
    d.polygon([(w * 0.3, h * 0.6), (w * 0.7, h * 0.6), (w * 0.5, h * 0.98)], fill=255)
    return m.rotate(ang, resample=Image.BICUBIC, expand=True).point(lambda v: 255 if v > 120 else 0)


def leaf_mask(size, ang):
    w, h = size
    m = Image.new('L', (w, h), 0); d = ImageDraw.Draw(m)
    pts = [(w * 0.5 + math.sin(t) * w * 0.34 * math.sin(t * 0.5 + 0.2) ** 0.6, h * (0.03 + 0.94 * t / math.pi)) for t in np.linspace(0, math.pi, 30)]
    pts += [(w - x, y) for x, y in reversed(pts)]
    d.polygon(pts, fill=255)
    return m.rotate(ang, resample=Image.BICUBIC, expand=True).point(lambda v: 255 if v > 120 else 0)


def peony(R, P, seed=1):
    """牡丹：外圈、中圈、內圈花瓣一層層疊上去，旁邊配葉子"""
    S = int(R * 3.4)
    out = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    c = S // 2
    rng = random.Random(seed)

    def put(layer, x, y):
        lay, pad = shadowed(layer, (3, 4), 4, 0.3)
        out.alpha_composite(lay, (int(x - layer.width / 2) - pad, int(y - layer.height / 2) - pad))

    for a in (20, 150, 265):                    # 葉子
        m = leaf_mask((int(R * 0.75), int(R * 1.5)), -a + 90)
        put(embroider(m, P['leaf'], 8, P['gold'], 4, seed), c + math.cos(math.radians(a)) * R * 1.15, c + math.sin(math.radians(a)) * R * 1.15)
    for ring, (n, dist, sz) in enumerate(((8, 0.78, 0.98), (6, 0.48, 0.8), (4, 0.2, 0.6))):
        for i in range(n):
            a = 360 / n * i + ring * 22 + rng.uniform(-6, 6)
            m = petal_mask((int(R * sz), int(R * sz * 1.15)), -a - 90)
            lay = embroider(m, P['petal'][ring:] + P['petal'][-1:], max(5, int(R * 0.085)), P['gold'], 4, seed + i)
            put(lay, c + math.cos(math.radians(a)) * R * dist, c + math.sin(math.radians(a)) * R * dist)
    m = Image.new('L', (int(R * 0.5), int(R * 0.5)), 0)
    ImageDraw.Draw(m).ellipse((2, 2, m.width - 3, m.height - 3), fill=255)
    put(embroider(m, [P['gold_l'], P['gold']], 6, P['gold'], 3, seed), c, c)
    return out


def waves(w, h, P):
    """海水紋：一排排半圓，每個半圓由外到內換色"""
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    R = 74
    for row in range(3, -1, -1):
        y = h - row * R * 0.55 + R * 0.25
        for col in range(-1, w // (R * 2) + 2):
            x = col * R * 2 + (R if row % 2 else 0)
            m = Image.new('L', (R * 2, R * 2), 0)
            ImageDraw.Draw(m).ellipse((0, 0, R * 2 - 1, R * 2 - 1), fill=255)
            lay = embroider(m, P['wave'], 11, P['gold'], 4, row * 31 + col)
            out.alpha_composite(lay, (int(x - R), int(y - R)))
    return out


def ring_frame(R, wd, P):
    S = (R + wd) * 2 + 8
    m = Image.new('L', (S, S), 0); d = ImageDraw.Draw(m)
    c = S // 2
    d.ellipse((c - R - wd, c - R - wd, c + R + wd, c + R + wd), fill=255)
    d.ellipse((c - R, c - R, c + R, c + R), fill=0)
    return embroider(m, [P['gold_l'], P['gold'], P['gold_l']], max(4, wd // 4), P['gold_d'], 4, 5)


def meander(size, P, lw=7):
    """回紋方框（放在圓框四個角後面）"""
    m = Image.new('L', (size, size), 0); d = ImageDraw.Draw(m)
    s = size
    for k in range(3):
        o = 6 + k * s * 0.13
        pts = [(o, s - 6), (o, o), (s - o, o), (s - o, s - o - s * 0.13 * (k < 2)), (o + s * 0.2, s - o - s * 0.13 * (k < 2))] if k < 2 else [(o, s - o), (o, o), (s - o, o)]
        d.line(pts, fill=255, width=lw, joint='curve')
    return embroider(m, [P['gold_l']], 3, P['gold'], 2, 9)


# ------------------------------------------------------------ 配色
G = dict(gold=rgb('#C99A3C'), gold_l=rgb('#F2D79A'), gold_d=rgb('#8E6A22'))
PALETTES = [
    dict(name='① 正紅金線（最接近參考範本）', bg=('#B01218', '#6E0409'), text='#FBE7C2', accent='#F6D58C', mark=(255, 220, 160),
         cloud=[rgb('#F7EBD3'), rgb('#E2572B'), rgb('#1F8A8A'), rgb('#F2D79A'), rgb('#C4281E')],
         petal=[rgb('#F7EBD3'), rgb('#F29C8A'), rgb('#D9432F'), rgb('#A51C16')], leaf=[rgb('#1F8A8A'), rgb('#7CC6B4'), rgb('#145E66')],
         wave=[rgb('#F7EBD3'), rgb('#1F8A8A'), rgb('#F2D79A'), rgb('#145E66'), rgb('#E2572B')], **G),
    dict(name='② 青花瓷藍白', bg=('#FBFAF5', '#EEF2F6'), text='#1F3566', accent='#1F3F8F', mark=(40, 70, 150),
         cloud=[rgb('#FFFFFF'), rgb('#8FB0E0'), rgb('#2F5BB5'), rgb('#DCE8F7'), rgb('#17357A')],
         petal=[rgb('#FFFFFF'), rgb('#B9CFF0'), rgb('#5C86D0'), rgb('#21459B')], leaf=[rgb('#2F5BB5'), rgb('#9FBDE8'), rgb('#17357A')],
         wave=[rgb('#FFFFFF'), rgb('#2F5BB5'), rgb('#DCE8F7'), rgb('#17357A'), rgb('#8FB0E0')],
         gold=rgb('#B8923A'), gold_l=rgb('#EBD49A'), gold_d=rgb('#8E6A22')),
    dict(name='③ 午夜藍金線', bg=('#1E2D52', '#0E1830'), text='#F3E6C8', accent='#F0D08A', mark=(240, 210, 140),
         cloud=[rgb('#F7EBD3'), rgb('#C9A45C'), rgb('#B8322E'), rgb('#F2D79A'), rgb('#7C1F22')],
         petal=[rgb('#F7EBD3'), rgb('#F0A99A'), rgb('#C93A32'), rgb('#8E1C1C')], leaf=[rgb('#3C8C8C'), rgb('#9AD0C4'), rgb('#1F5C66')],
         wave=[rgb('#F7EBD3'), rgb('#C9A45C'), rgb('#33508F'), rgb('#F2D79A'), rgb('#B8322E')], **G),
    dict(name='④ 象牙白・紅金繡線', bg=('#FBF7EE', '#F3E9D8'), text='#5A2A22', accent='#A3262A', mark=(170, 60, 50),
         cloud=[rgb('#FFF8EA'), rgb('#E8A07A'), rgb('#C4382C'), rgb('#F2D79A'), rgb('#8E1C1C')],
         petal=[rgb('#FFF4EE'), rgb('#F4B4A6'), rgb('#D9483A'), rgb('#A51C16')], leaf=[rgb('#6FA58A'), rgb('#B9DCC8'), rgb('#3F7560')],
         wave=[rgb('#FFF8EA'), rgb('#C4382C'), rgb('#F2D79A'), rgb('#8E1C1C'), rgb('#E8A07A')], **G),
    dict(name='⑤ 酒紅・粉金繡線', bg=('#6A1C28', '#3E0D17'), text='#F7E3D6', accent='#F1CFA0', mark=(250, 200, 180),
         cloud=[rgb('#FBE9E1'), rgb('#E9A9A6'), rgb('#C96B78'), rgb('#F2D79A'), rgb('#8C2F45')],
         petal=[rgb('#FFF1EC'), rgb('#F5C2BE'), rgb('#DE7F8C'), rgb('#A63A55')], leaf=[rgb('#8FB8A2'), rgb('#CFE5D6'), rgb('#55806A')],
         wave=[rgb('#FBE9E1'), rgb('#C96B78'), rgb('#F2D79A'), rgb('#8C2F45'), rgb('#E9A9A6')], **G),
]


def build(P):
    c0, c1 = np.array(rgb(P['bg'][0]), float), np.array(rgb(P['bg'][1]), float)
    yy, xx = np.mgrid[0:H, 0:W]
    t = np.clip(np.hypot((xx - W * 0.35) / W, (yy - H * 0.25) / H) * 1.25, 0, 1)[..., None]
    im = Image.fromarray((c0 * (1 - t) + c1 * t).astype('uint8')).convert('RGBA')

    # 淡淡的線稿浮水印（大朵祥雲的輪廓）
    wm = Image.new('L', (W, H), 0)
    for (x, y, s, f) in ((-60, 880, 520, False), (360, 1180, 560, True), (300, 60, 420, True)):
        m = cloud_mask((s, int(s * 0.55)), f)
        edge = ImageChops.subtract(m, erode(m, 3))
        for k in (14, 28):
            edge = ImageChops.lighter(edge, ImageChops.subtract(erode(m, k), erode(m, k + 3)))
        wm.paste(edge, (x, y), edge)
    mark = Image.new('RGBA', (W, H), P['mark'] + (0,)); mark.putalpha(wm.point(lambda v: int(v * 0.13)))
    im.alpha_composite(mark)

    def put(layer, x, y, sh=True):
        if sh:
            lay, pad = shadowed(layer)
            im.alpha_composite(lay, (int(x) - pad, int(y) - pad))
        else:
            im.alpha_composite(layer, (int(x), int(y)))

    put(waves(W, 190, P), 0, H - 190, False)
    put(embroider(cloud_mask((330, 170), True), P['cloud'], 12, P['gold'], 5, 3), 450, 70)
    put(embroider(cloud_mask((250, 130)), P['cloud'], 10, P['gold'], 5, 4), -30, 1130)
    put(peony(118, P, 1), -150, -140, False)

    # 金線圓框＋回紋角＋照片
    cx, cy, R = W // 2, 640, 236
    for sx in (-1, 1):
        for sy in (-1, 1):
            mz = meander(120, P)
            if sx > 0: mz = mz.transpose(Image.FLIP_LEFT_RIGHT)
            if sy > 0: mz = mz.transpose(Image.FLIP_TOP_BOTTOM)
            put(mz, cx + sx * (R + 24) - (120 if sx > 0 else 0), cy + sy * (R + 24) - (120 if sy > 0 else 0))
    ph = Image.open(os.path.join(ROOT, 'assets/video/wink.jpg')).convert('RGB').crop((0, 30, 720, 750)).resize((R * 2, R * 2), Image.LANCZOS)
    pm = Image.new('L', (R * 2, R * 2), 0); ImageDraw.Draw(pm).ellipse((0, 0, R * 2 - 1, R * 2 - 1), fill=255)
    im.paste(ph, (cx - R, cy - R), pm)
    ring = ring_frame(R - 4, 26, P)
    put(ring, cx - ring.width // 2, cy - ring.height // 2)
    put(peony(92, P, 7), cx + R - 190, cy + R - 200, False)
    put(embroider(cloud_mask((230, 120), True), P['cloud'], 9, P['gold'], 5, 8), cx + 40, cy + R + 10)

    # 囍字圓章與文字
    d = ImageDraw.Draw(im)
    xi = Image.new('L', (150, 150), 0)
    ImageDraw.Draw(xi).text((75, 78), '囍', font=font(118), fill=255, anchor='mm')
    put(embroider(xi, [P['gold_l'], P['gold']], 4, P['gold_d'], 2, 2), cx - 75, 190)
    d.text((cx, 1010), '蕭苰栯  ♥  洪韻雯', font=font(50), fill=P['text'], anchor='mm')
    d.text((cx, 1090), '我 們 結 婚 啦', font=font(34, False), fill=P['accent'], anchor='mm')
    d.line((cx - 150, 1140, cx + 150, 1140), fill=P['accent'], width=2)
    d.text((cx, 1186), '2026.11.06（五）午宴 11:00', font=font(28, False), fill=P['text'], anchor='mm')
    d.text((cx, 1232), '高雄日航酒店・三樓宴會廳', font=font(28, False), fill=P['text'], anchor='mm')
    bx0, by0, bx1, by1 = 110, 1320, W - 110, 1410        # 缺角的標題框
    n = 16
    d.line([(bx0 + n, by0), (bx1 - n, by0), (bx1 - n, by0 + n), (bx1, by0 + n), (bx1, by1 - n), (bx1 - n, by1 - n), (bx1 - n, by1),
            (bx0 + n, by1), (bx0 + n, by1 - n), (bx0, by1 - n), (bx0, by0 + n), (bx0 + n, by0 + n), (bx0 + n, by0)], fill=P['accent'], width=3)
    d.text((cx, (by0 + by1) // 2), '婚 宴 資 訊', font=font(34), fill=P['accent'], anchor='mm')
    return im.convert('RGB').resize((W // 2, H // 2), Image.LANCZOS)


if __name__ == '__main__':
    pad = 20
    sheet = Image.new('RGB', (5 * 390 + 6 * pad, 844 + 2 * pad + 44), '#2B2B2B')
    d = ImageDraw.Draw(sheet)
    for i, P in enumerate(PALETTES):
        x = pad + i * (390 + pad)
        card = build(P)
        card.save(os.path.join(ROOT, 'work', f'embroidery-demo-{i + 1}.jpg'), quality=92)
        sheet.paste(card, (x, pad + 44))
        d.text((x + 195, pad + 20), P['name'], font=font(20), fill='#FFFFFF', anchor='mm')
        print('done', i + 1)
    sheet.save(os.path.join(ROOT, 'work', 'embroidery-demos.jpg'), quality=90)
