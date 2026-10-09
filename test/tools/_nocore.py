import os, re, shutil
SD = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa/history/states'
BAK = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa/history/_states_backup_before_nocore'
if not os.path.isdir(BAK):
    shutil.copytree(SD, BAK)
    print('已备份 -> ' + os.path.basename(BAK))
else:
    print('备份已存在')
n = 0; removed = 0
for fn in sorted(os.listdir(SD)):
    p = os.path.join(SD, fn)
    raw = open(p, 'rb').read()
    bom = raw.startswith(b'\xef\xbb\xbf')
    t = raw.decode('utf-8-sig')
    lines = t.splitlines()
    keep = [l for l in lines if not re.match(r'^\s*add_core_of\s*=', l)]
    if len(keep) != len(lines):
        removed += len(lines) - len(keep)
        body = '\n'.join(keep) + '\n'
        open(p, 'wb').write((b'\xef\xbb\xbf' if bom else b'') + body.encode('utf-8'))
        n += 1
print('处理 %d 个文件, 删除 %d 行 add_core_of' % (n, removed))
