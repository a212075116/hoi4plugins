import re, shutil, os
M = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa/common/occupation_laws/occupation_laws.txt'
blk = open(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/no_garrison_block.txt', encoding='utf-8').read().rstrip('\n')
txt = open(M, encoding='utf-8-sig', errors='replace').read()
lines = txt.splitlines()

# 备份
bak = M + '.bak_before_no_garrison'
shutil.copyfile(M, bak)
print('已备份 -> ' + os.path.basename(bak))

# 找到 missing_garrison_scaled_effect 的结尾, 插在它后面
start = None
for i, l in enumerate(lines):
    if re.match(r'^missing_garrison_scaled_effect\s*=\s*\{', l):
        start = i; break
assert start is not None
depth = 0
end = None
for i in range(start, len(lines)):
    depth += lines[i].count('{') - lines[i].count('}')
    if depth == 0 and i > start:
        end = i; break
print('missing_garrison_scaled_effect: 行 %d..%d' % (start+1, end+1))

# 检查是否已存在 no_garrison 顶层定义
if any(re.match(r'^no_garrison\s*=\s*\{', l) for l in lines):
    print('mod 里已有 no_garrison, 不再插入')
else:
    new = lines[:end+1] + [''] + blk.splitlines() + [''] + lines[end+1:]
    open(M, 'w', encoding='utf-8-sig', newline='\n').write('\n'.join(new) + '\n')
    print('已插入 no_garrison (共 %d 行)' % len(new))

# 复核
a = open(M, encoding='utf-8-sig', errors='replace').read().splitlines()
print('=== 插入后的顶层 law 列表 ===')
for i, l in enumerate(a):
    if re.match(r'^[A-Za-z_][A-Za-z0-9_]*\s*=\s*\{', l):
        print('  行%4d: %s' % (i+1, l))
