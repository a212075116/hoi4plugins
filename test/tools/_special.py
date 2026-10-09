import os, re, glob
SD = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa/history/states'
targets = [7, 31, 423, 425, 426, 427, 430, 432, 433, 434, 435]
files = {}
for fn in os.listdir(SD):
    m = re.match(r'^(\d+)-', fn)
    if m: files[int(m.group(1))] = fn
print('=== 保持 tag 的州在 mod 里的定义 ===')
for t in targets:
    fn = files.get(t)
    if not fn:
        print('  id=%d  (mod 里没有对应文件!)' % t)
        continue
    p = os.path.join(SD, fn)
    t2 = open(p, encoding='utf-8-sig', errors='replace').read()
    mo = re.search(r'^\s*owner\s*=\s*([A-Za-z0-9_]+)', t2, re.M)
    cores = re.findall(r'add_core_of\s*=\s*([A-Za-z0-9_]+)', t2)
    prov = re.search(r'provinces\s*=\s*\{([^}]*)\}', t2, re.S)
    nprov = len(prov.group(1).split()) if prov else 0
    cat = re.search(r'state_category\s*=\s*(\w+)', t2)
    print('  id=%-3d %-22s owner=%-5s cores=%-14s provinces=%d  category=%s' % (
        t, fn, mo.group(1) if mo else '?', ','.join(cores[:3]) if cores else '(空)', nprov,
        cat.group(1) if cat else '?'))
print()
print('=== 对照: 变 0 的前 5 个州 ===')
for t in [1, 2, 3, 4, 5]:
    fn = files.get(t)
    if not fn: print('  id=%d (无文件)' % t); continue
    t2 = open(os.path.join(SD, fn), encoding='utf-8-sig', errors='replace').read()
    mo = re.search(r'^\s*owner\s*=\s*([A-Za-z0-9_]+)', t2, re.M)
    cores = re.findall(r'add_core_of\s*=\s*([A-Za-z0-9_]+)', t2)
    print('  id=%-3d %-22s owner=%-5s cores=%s' % (t, fn, mo.group(1) if mo else '?', ','.join(cores[:3]) if cores else '(空)'))
print()
print('=== mod 里 state id 的最大/最小 ===')
ids = sorted(files.keys())
print('  min=%d max=%d 共 %d 个' % (ids[0], ids[-1], len(ids)))
print('  >=423 的: ' + str([i for i in ids if i >= 423]))
