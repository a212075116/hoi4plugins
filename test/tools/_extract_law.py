# 从原版 occupation_laws.txt 抽出 no_garrison 的完整定义
import re
V = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/common/occupation_laws/occupation_laws.txt'
txt = open(V, encoding='utf-8-sig', errors='replace').read()
lines = txt.splitlines()
start = None
for i, l in enumerate(lines):
    if re.match(r'^no_garrison\s*=\s*\{', l):
        start = i; break
assert start is not None, 'no_garrison not found'
depth = 0
end = None
for i in range(start, len(lines)):
    depth += lines[i].count('{') - lines[i].count('}')
    if depth == 0 and i > start:
        end = i; break
block = lines[start:end+1]
print('no_garrison 定义: 行 %d..%d (%d 行)' % (start+1, end+1, len(block)))
print(chr(10).join('  ' + x for x in block))
open(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/no_garrison_block.txt', 'w', encoding='utf-8').write(chr(10).join(block) + chr(10))
print()
print('已存到 reports/no_garrison_block.txt')
