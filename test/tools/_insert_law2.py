import re, shutil, os
M = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa/common/occupation_laws/occupation_laws.txt'
BAK = M + '.bak_before_no_garrison'

# 从备份恢复
shutil.copyfile(BAK, M)
print('已从备份恢复')

# 读原始字节, 检查 BOM
raw = open(M, 'rb').read()
has_bom = raw.startswith(b'\xef\xbb\xbf')
print('原文件 BOM: %s' % has_bom)

# 用 utf-8-sig 读 (自动去 BOM)
txt = raw.decode('utf-8-sig')
lines = txt.splitlines()
print('行数: %d' % len(lines))

blk = open(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/no_garrison_block.txt', encoding='utf-8').read().rstrip('\n').splitlines()

# 找插入点
start = None
for i, l in enumerate(lines):
    if re.match(r'^missing_garrison_scaled_effect\s*=\s*\{', l):
        start = i; break
assert start is not None
depth = 0; end = None
for i in range(start, len(lines)):
    depth += lines[i].count('{') - lines[i].count('}')
    if depth == 0 and i > start:
        end = i; break
print('插入点: 行 %d 之后' % (end+1))

assert not any(re.match(r'^no_garrison\s*=\s*\{', l) for l in lines), '已有 no_garrison'
new = lines[:end+1] + [''] + blk + [''] + lines[end+1:]
body = '\n'.join(new) + '\n'

# 关键: 保持原有 BOM 状态, 编码就不带 BOM, 手动加回一个
out = (b'\xef\xbb\xbf' if has_bom else b'') + body.encode('utf-8')
open(M, 'wb').write(out)
print('已写回, %d 字节' % len(out))
print('检查前 6 字节: ' + ' '.join('%02x' % b for b in out[:6]))

# 复核
a = open(M, encoding='utf-8-sig').read().splitlines()
print('复核顶层 law:')
for i, l in enumerate(a):
    if re.match(r'^[A-Za-z_][A-Za-z0-9_]*\s*=\s*\{', l):
        print('  行%4d: %s' % (i+1, l))
