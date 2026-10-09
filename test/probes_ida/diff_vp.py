# diff_vp.py -- 把三个集合精确对齐, 解释 1711 / 1706 / 1703 的差异
import re, os, json, glob

MOD = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa'

# A: mod history/states 里 victory_points 定义的省份 id
A = set()
for fp in glob.glob(os.path.join(MOD, 'history/states/*.txt')):
    try: txt = open(fp, encoding='utf-8-sig', errors='ignore').read()
    except Exception: continue
    for blk in re.findall(r'victory_points\s*=\s*\{([^}]*)\}', txt):
        for mm in re.finditer(r'(\d+)\s+\d+', blk):
            A.add(int(mm.group(1)))

# B: 本地化表里的 VICTORY_POINTS_<id>
B = set()
for lang in ('simp_chinese',):
    for fp in glob.glob(os.path.join(MOD, 'localisation', lang, '*.yml')):
        try: lines = open(fp, encoding='utf-8-sig', errors='ignore').read().split(chr(10))
        except Exception: continue
        for line in lines:
            mm = re.match(r'^\s*(?:[A-Z]{3}_)?VICTORY_POINTS_(\d+)\s*:', line)
            if mm: B.add(int(mm.group(1)))

print('A = mod history/states 里有 victory_points 的省份数 : %d' % len(A))
print('B = 中文本地化 VICTORY_POINTS_<id> 条目数         : %d' % len(B))
print('')
print('A - B (定义了胜利点但没有中文本地化) : %d' % len(A - B))
print('   %s' % sorted(A - B)[:40])
print('B - A (有中文本地化但没定义胜利点)   : %d' % len(B - A))
print('   %s' % sorted(B - A)[:40])
print('A & B                                : %d' % len(A & B))
print('')
json.dump({'A': sorted(A), 'B': sorted(B)}, open(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/vp_sets.json', 'w'))
print('[写出] reports/vp_sets.json')