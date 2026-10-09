import os, re
ROOT = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa'
# 找 scripted_triggers 目录 + 抵抗相关的 trigger 定义
for dp, dn, fn in os.walk(ROOT):
    if 'scripted_triggers' in dp.lower():
        print('目录: ' + dp.replace(ROOT, ''))
        for f in fn: print('    ' + f)
print()
print('=== 搜 resistance 相关的 scripted_triggers 定义 ===')
for dp, dn, fn in os.walk(ROOT):
    for f in fn:
        if not f.endswith('.txt'): continue
        p = os.path.join(dp, f)
        try: t = open(p, encoding='utf-8-sig', errors='replace').read()
        except Exception: continue
        for m in re.finditer(r'^\s*([A-Za-z0-9_]*resistance[A-Za-z0-9_]*)\s*=\s*\{', t, re.M):
            ln = t[:m.start()].count(chr(10)) + 1
            print('  %s:%d  %s' % (p.replace(ROOT,''), ln, m.group(1)))
print()
print('=== 原版里同名 trigger 在哪定义 ===')
for dp, dn, fn in os.walk(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'):
    if 'scripted_triggers' not in dp.lower(): continue
    for f in fn:
        if not f.endswith('.txt'): continue
        p = os.path.join(dp, f)
        try: t = open(p, encoding='utf-8-sig', errors='replace').read()
        except Exception: continue
        for m in re.finditer(r'^\s*([A-Za-z0-9_]*resistance[A-Za-z0-9_]*)\s*=\s*\{', t, re.M):
            ln = t[:m.start()].count(chr(10)) + 1
            print('  %s:%d  %s' % (p.replace(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV',''), ln, m.group(1)))
