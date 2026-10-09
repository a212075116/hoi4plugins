import os, re, collections
SD = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa/history/states'
# 1) 收集 mod 定义的所有 tag
tags = set()
CT = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa/common/country_tags'
for root, dirs, files in os.walk(CT):
    for fn in files:
        try:
            for line in open(os.path.join(root, fn), encoding='utf-8-sig', errors='replace'):
                m = re.match(r'\s*([A-Za-z0-9_]{2,})\s*=', line)
                if m and '#' not in line.split('=')[0]: tags.add(m.group(1).upper())
        except Exception: pass
# mod countries 目录文件名也是 tag
for fn in os.listdir(r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa/common/countries'):
    tags.add(fn.split('-')[0].strip().upper())
for fn in os.listdir(r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa/history/countries'):
    tags.add(fn.split('-')[0].strip().upper())
# 2) 原版的 tag (也要算合法)
VT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/common/country_tags'
for root, dirs, files in os.walk(VT):
    for fn in files:
        try:
            for line in open(os.path.join(root, fn), encoding='utf-8-sig', errors='replace'):
                m = re.match(r'\s*([A-Za-z0-9_]{2,})\s*=', line)
                if m: tags.add(m.group(1).upper())
        except Exception: pass
print('合法 tag 数 (mod + 原版): %d' % len(tags))
print()
# 3) 检查所有 add_core_of / owner / add_claim_by
bad = collections.Counter()
allcore = collections.Counter()
n = 0
for fn in os.listdir(SD):
    try: t = open(os.path.join(SD, fn), encoding='utf-8-sig', errors='replace').read()
    except Exception: continue
    n += 1
    for m in re.finditer(r'add_core_of\s*=\s*([A-Za-z0-9_]+)', t):
        k = m.group(1).upper()
        allcore[k] += 1
        if k not in tags: bad[k] += 1
    for m in re.finditer(r'^\s*owner\s*=\s*([A-Za-z0-9_]+)', t, re.M):
        k = m.group(1).upper()
        if k not in tags: bad['OWNER:' + k] += 1
print('add_core_of 出现的不同 tag 数: %d' % len(allcore))
print('=== 非法 tag ===')
if bad:
    for k, v in bad.most_common(30): print('  %-12s x%d' % (k, v))
else:
    print('  (无)')
