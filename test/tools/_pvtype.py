import os, re
SD = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa/history/states'
# 解析 definition.csv
defs = {}
with open(os.path.join(r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa', 'map', 'definition.csv'), encoding='utf-8-sig', errors='replace') as f:
    for line in f:
        parts = line.strip().split(';')
        if len(parts) >= 6 and parts[0].isdigit():
            defs[int(parts[0])] = parts[4]   # land / sea
files = {}
for fn in os.listdir(SD):
    m = re.match(r'^(\d+)-', fn)
    if m: files[int(m.group(1))] = fn
keep = [7, 31, 423, 425, 426, 427, 430, 432, 433, 434, 435]
zero = [2, 5, 8, 11, 12, 14, 15, 17, 18, 20, 24, 26, 29, 35, 49, 431]
def pv(sid):
    fn = files.get(sid)
    if not fn: return None
    t = open(os.path.join(SD, fn), encoding='utf-8-sig', errors='replace').read()
    mp = re.search(r'provinces\s*=\s*\{([^}]*)\}', t, re.S)
    return [int(x) for x in mp.group(1).split() if x.isdigit()] if mp else []
print('=== 保持 tag 的 11 个州的省份类型 ===')
for s in keep:
    ps = pv(s)
    types = [defs.get(p, '?') for p in ps]
    print('  id=%-4d 省份数=%-3d land=%d sea=%d  %s' % (s, len(ps), types.count('land'), types.count('sea'), types[:8]))
print()
print('=== 变 0 的对照州 ===')
for s in zero:
    ps = pv(s)
    types = [defs.get(p, '?') for p in ps]
    print('  id=%-4d 省份数=%-3d land=%d sea=%d  %s' % (s, len(ps), types.count('land'), types.count('sea'), types[:8]))
