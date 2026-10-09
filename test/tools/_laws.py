import re, os
def laws(p):
    out = []
    try:
        txt = open(p, encoding='utf-8-sig', errors='replace').read()
    except Exception as e:
        return ['(读取失败 %s)' % e]
    # 顶层 key = 占领法名 (缩进 0)
    for line in txt.splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        if line[0] not in ' \t':
            m = re.match(r'([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{', line)
            if m:
                out.append(m.group(1))
    return out
V = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/common/occupation_laws/occupation_laws.txt'
M = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa/common/occupation_laws/occupation_laws.txt'
vl = laws(V)
ml = laws(M)
print('原版占领法 (%d):' % len(vl))
for x in vl: print('  ' + x)
print()
print('mod 占领法 (%d):' % len(ml))
for x in ml: print('  ' + x)
print()
missing = [x for x in vl if x not in ml]
extra = [x for x in ml if x not in vl]
print('mod 缺失 (原版有, mod 没有) (%d):' % len(missing))
for x in missing: print('  ' + x)
print()
print('mod 新增 (%d):' % len(extra))
for x in extra: print('  ' + x)
