import re
V = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/common/resistance_activity/resistance_activity.txt'
M = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa/common/resistance_activity/resistance_activity.txt'
vl = open(V, encoding='utf-8-sig', errors='replace').read().splitlines()
ml = open(M, encoding='utf-8-sig', errors='replace').read().splitlines()
print('原版 %d 行, mod %d 行' % (len(vl), len(ml)))
print()
print('=== 原版 395-412 行 ===')
for i in range(394, min(412, len(vl))): print('  %4d: %s' % (i+1, vl[i]))
print()
print('=== mod 398-415 行 ===')
for i in range(397, min(415, len(ml))): print('  %4d: %s' % (i+1, ml[i]))
print()
# 两边顶层 activity key 对比
def keys(ls):
    out = []
    for i, l in enumerate(ls):
        if re.match(r'^[A-Za-z_][A-Za-z0-9_]*\s*=\s*\{', l): out.append((i+1, l.split('=')[0].strip()))
    return out
vk = keys(vl); mk = keys(ml)
print('原版 activity 数: %d' % len(vk))
print('mod  activity 数: %d' % len(mk))
print()
vs = set(x[1] for x in vk); ms = set(x[1] for x in mk)
print('=== mod 缺失的 activity (%d) ===' % len(vs - ms))
for x in sorted(vs - ms): print('  ' + x)
print()
print('=== mod 新增的 (%d) ===' % len(ms - vs))
for x in sorted(ms - vs): print('  ' + x)
