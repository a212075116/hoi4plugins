# diff_vp2.py -- 把动态读到的省份 id 与 vp_sets.json 对齐
import json, re, os
J = json.load(open(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/vp_sets.json'))
A = set(J['A']); B = set(J['B'])
print('A(定义胜利点)=%d  B(本地化)=%d  A&B=%d' % (len(A), len(B), len(A & B)))
print('')
print('A - B  (%d):' % len(A - B))
for x in sorted(A - B): print('    %d' % x)
print('')
# 读动态枚举文件, 提取所有 有名字 的 id
f = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/20261009_015321_CGameState_CProvince_名字完整枚举.txt'
dyn = set()
for line in open(f, encoding='utf-8'):
    mm = re.match(r'^(\d+)\s+0x[0-9a-f]+\s+(\d+)\s+(\d+)\s+(.*)$', line.strip())
    if mm:
        nm = mm.group(4).strip()
        if nm and not nm.startswith('(该省份无胜利点)') and not nm.startswith('('):
            dyn.add(int(mm.group(2)))
print('动态读到有名字的省份 id 数: %d' % len(dyn))
print('')
print('本地化有但动态没匹配到 (B & A) - dyn : %d' % len((A & B) - dyn))
for x in sorted((A & B) - dyn): print('    %d' % x)
print('')
print('动态有但本地化没有 dyn - B : %d' % len(dyn - B))
for x in sorted(dyn - B)[:20]: print('    %d' % x)