import os, re, shutil
SD = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa/history/states'
BAK = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa/history/_states_backup_before_ctrl2'
if not os.path.isdir(BAK):
    shutil.copytree(SD, BAK); print('已备份')
else:
    print('备份已存在')
n = 0
for fn in sorted(os.listdir(SD)):
    p = os.path.join(SD, fn)
    raw = open(p, 'rb').read()
    bom = raw.startswith(b'\xef\xbb\xbf')
    t = raw.decode('utf-8-sig')
    if re.search(r'controller\s*=', t): continue
    mo = re.search(r'^(\s*)owner\s*=\s*([A-Za-z0-9_]+)', t, re.M)
    if not mo: continue
    indent = mo.group(1); tag = mo.group(2)
    # 用日期块语法, 日期取 1936.1.1 (早于 bookmark 的 500.1.1)
    ins = '\n' + indent + '1936.1.1 = {'
    ins += '\n' + indent + '\tcontroller = ' + tag
    ins += '\n' + indent + '}'
    new = t[:mo.end()] + ins + t[mo.end():]
    open(p, 'wb').write((b'\xef\xbb\xbf' if bom else b'') + new.encode('utf-8'))
    n += 1
print('已给 %d 个州加日期块形式的 controller' % n)
t = open(os.path.join(SD, '2-State_2.txt'), encoding='utf-8-sig').read()
print('--- 2-State_2.txt 抽查 ---')
for l in t.splitlines()[:22]: print('  ' + l)
