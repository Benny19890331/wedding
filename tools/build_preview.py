# 產生「預覽版」：給新人自己先看、留意見用的版本（發布成 Claude Artifact）
# 和正式版的差別：不嵌 Google 地圖（預覽環境不允許嵌入其他網站）、表單不會真的送出、沒有下載行事曆檔的按鈕
# 用法：python tools/build_preview.py   → work/preview/
import os, re, shutil

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT = os.path.join(ROOT, 'work', 'preview')

s = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
head = s[s.index('<head>') + 6:s.index('</head>')]
body = s[s.index('<body>') + 6:s.index('</body>')]

fonts = re.search(r'<link href="https://fonts\.googleapis\.com/css2[^>]+>', head).group(0)
page = '\n'.join([
    '<title>蕭苰栯 ♥ 洪韻雯 喜帖</title>',
    fonts,
    '<link rel="stylesheet" href="css/style.css">',
    body,
])
page = re.sub(r'\?v=\d+', '', page)                                   # 預覽環境的檔案路徑不帶版本參數
page = re.sub(r'    <div class="map">.*?</div>\n', '    <p class="map-note">（正式版這裡會有 Google 地圖，預覽版先不顯示）</p>\n', page, flags=re.S)
page = re.sub(r'\s*<a class="btn btn-ghost" href="assets/wedding\.ics">[^<]*</a>', '', page)
assert '<iframe' not in page and 'wedding.ics' not in page

if os.path.isdir(OUT):
    for root, dirs, files in os.walk(OUT):
        for f in files:
            os.remove(os.path.join(root, f))
os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8').write(page)

files = {}
def put(rel, content=None):
    dst = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if content is None:
        shutil.copy(os.path.join(ROOT, rel), dst)
    else:
        open(dst, 'w', encoding='utf-8').write(content)
    files[rel] = rel

css = open(os.path.join(ROOT, 'css', 'style.css'), encoding='utf-8').read()
css += '\n.map-note { text-align: center; color: var(--muted); font-size: 13px; margin: 14px 0 0; }\n'
put('css/style.css', css)
put('js/main.js')
put('config.js', "// 預覽版設定：表單不會真的送出\nwindow.WEDDING_CONFIG = { API_URL: '', PREVIEW: true, START: '2026-11-06T11:00:00+08:00' };\n")
put('assets/gift-qr.png')
for d in ('assets/video', 'assets/audio', 'assets/fonts', 'assets/gif'):
    for f in sorted(os.listdir(os.path.join(ROOT, d))):
        if not f.endswith('.txt'):
            put(d + '/' + f)

total = sum(os.path.getsize(os.path.join(OUT, f)) for f in files)
print('files', len(files), 'total MB', round(total / 1e6, 2))
import json
json.dump(files, open(os.path.join(OUT, 'files.json'), 'w'), indent=1)
