# 把內海字體裁成只含兩人名字的小檔（網頁用）
# 用法：python -I tools/subset_font.py <完整字體檔> <輸出.woff2>
import site, sys
sys.path.append(site.getusersitepackages())      # -I 模式不會自動載入使用者安裝的套件，手動加入
from fontTools import subset
from fontTools.ttLib import TTFont

NAMES = '蕭苰栯洪韻雯'
src, dst = sys.argv[1], sys.argv[2]
opts = subset.Options()
opts.flavor = 'woff2'
opts.layout_features = []
opts.name_IDs = [1, 2, 4, 6, 13, 14]             # 保留字體名稱與授權資訊
opts.notdef_outline = True
font = TTFont(src)
sub = subset.Subsetter(opts)
sub.populate(text=NAMES)
sub.subset(font)
font.flavor = 'woff2'
font.save(dst)
check = TTFont(dst)
cmap = check.getBestCmap()
print('glyphs kept:', ''.join(c for c in NAMES if ord(c) in cmap), '| missing:', ''.join(c for c in NAMES if ord(c) not in cmap) or 'none')
