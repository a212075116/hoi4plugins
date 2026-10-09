import os, re, collections
def stat(SD, tag):
    files = [f for f in os.listdir(SD) if f.endswith('.txt')]
    n_owner = n_ctrl = 0
    for fn in files:
        try:
            t = open(os.path.join(SD, fn), encoding='utf-8-sig', errors='replace').read()
        except Exception: continue
        if re.search(r'^\s*owner\s*=', t, re.M): n_owner += 1
        if re.search(r'^\s*controller\s*=', t, re.M): n_ctrl += 1
    print('%s: %d 个 state 文件, 有 owner %d, 有 controller %d' % (tag, len(files), n_owner, n_ctrl))
    return files
f1 = stat(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/history/states', '原版')
f2 = stat(r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa/history/states', 'mod')
print()
print('=== mod 前 3 个 state 文件的完整内容 ===')
for fn in sorted(f2)[:3]:
    print('--- ' + fn + ' ---')
    t = open(os.path.join(r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa/history/states', fn), encoding='utf-8-sig', errors='replace').read()
    for l in t.splitlines()[:22]: print('  ' + l)
    print()
print('=== 原版前 2 个(state) ===')
for fn in sorted(f1)[:2]:
    print('--- ' + fn + ' ---')
    t = open(os.path.join(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/history/states', fn), encoding='utf-8-sig', errors='replace').read()
    for l in t.splitlines()[:22]: print('  ' + l)
    print()
