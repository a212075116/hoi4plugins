import os, re
SD = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa/history/states'
n = 0; addcore_lines = 0; strict = 0; files_with = 0
total_lines = 0
for fn in sorted(os.listdir(SD)):
    p = os.path.join(SD, fn)
    if not os.path.isfile(p): continue
    n += 1
    t = open(p, encoding='utf-8-sig', errors='replace').read()
    total_lines += len(t.splitlines())
    lines = t.splitlines()
    c = [l for l in lines if re.match(r'^\s*add_core_of\s*=', l)]
    addcore_lines += len(c)
    if c: files_with += 1
    strict += len(re.findall(r'add_core_of\s*=', t))
print('文件数: %d' % n)
print('总行数: %d' % total_lines)
print('严格匹配 ^\\s*add_core_of\\s*= 的行数: %d' % addcore_lines)
print('含 add_core_of 的文件数: %d' % files_with)
print('任意位置匹配 add_core_of\\s*= 的次数: %d' % strict)
print()
print('注: 删除实验记录是 393 个文件 / 753 行; 若现在严格匹配为 753 且 393 个文件, 则已完全恢复。')
