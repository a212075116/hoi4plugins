import os, re, shutil
SD = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa/history/states'
BAK = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa/history/_states_backup_before_controller'
if not os.path.isdir(BAK):
    shutil.copytree(SD, BAK)
    print('已备份 446 个 state 文件 -> ' + os.path.basename(BAK))
else:
    print('备份已存在')

n = 0; skipped = 0
for fn in sorted(os.listdir(SD)):
    p = os.path.join(SD, fn)
    raw = open(p, 'rb').read()
    bom = raw.startswith(b'\xef\xbb\xbf')
    t = raw.decode('utf-8-sig')
    if re.search(r'^\s*controller\s*=', t, re.M):
        skipped += 1; continue
    mo = re.search(r'^(\s*)owner\s*=\s*([A-Za-z0-9_]+)', t, re.M)
    if not mo:
        skipped += 1; continue
    indent = mo.group(1); tag = mo.group(2)
    # 在 owner 行后插入同样缩进的 controller
    new = t[:mo.end()] + '\n' + indent + 'controller = ' + tag + t[mo.end():]
    out = (b'\xef\xbb\xbf' if bom else b'') + new.encode('utf-8')
    open(p, 'wb').write(out)
    n += 1
print('已添加 controller 到 %d 个文件, 跳过 %d' % (n, skipped))
# 抽查
import random
for fn in sorted(os.listdir(SD))[:2]:
    t = open(os.path.join(SD, fn), encoding='utf-8-sig').read().splitlines()
    print('--- ' + fn + ' ---')
    for l in t[:20]: print('  ' + l)
