import re, collections
f = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/20261009_015321_CGameState_CCharacter_id与名字完整枚举.txt'
rows = []
for line in open(f, encoding='utf-8'):
    mm = re.match(r'^(\d+)\s+(0x[0-9a-f]+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(.*)$', line.rstrip())
    if mm and mm.group(2).startswith('0x'):
        rows.append({'i': int(mm.group(1)), 'ptr': mm.group(2),
                     'id18': int(mm.group(3)) if mm.group(3).isdigit() else None,
                     'id70': int(mm.group(4)) if mm.group(4).isdigit() else None,
                     'vt': mm.group(5), 'name': mm.group(6)})
print('解析行数: %d' % len(rows))
names = [r['name'] for r in rows]
print('名字去重后: %d' % len(set(names)))
print('')
v18 = [r['id18'] for r in rows if r['id18'] is not None]
v70 = [r['id70'] for r in rows if r['id70'] is not None]
print('+0x18  去重: %d   范围 %s..%s' % (len(set(v18)), min(v18), max(v18)))
print('+0x70  去重: %d   范围 %s..%s' % (len(set(v70)), min(v70), max(v70)))
print('')
print('=== +0x18 的取值分布(前 20) ===')
for v, c in collections.Counter(v18).most_common(20):
    print('    %-10d x%d' % (v, c))
print('')
print('=== +0x70 的取值分布(前 20) ===')
for v, c in collections.Counter(v70).most_common(20):
    print('    %-10d x%d' % (v, c))
print('')
print('=== 同一 +0x18 值的样本(取最多的那个) ===')
top = collections.Counter(v18).most_common(1)[0][0]
sel = [r for r in rows if r['id18'] == top][:12]
for r in sel:
    print('    i=%-6d id18=%-8d id70=%-8d name=%s' % (r['i'], r['id18'], r['id70'], r['name']))
print('')
print('=== 前 40 行的 id18 / id70 对照 ===')
for r in rows[:40]:
    print('    i=%-6d id18=%-8s id70=%-8s %s' % (r['i'], r['id18'], r['id70'], r['name']))