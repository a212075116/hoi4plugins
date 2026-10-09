import re, collections
f = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/20261009_015321_CGameState_CCharacter_id与名字完整枚举.txt'
rows = []
for line in open(f, encoding='utf-8'):
    mm = re.match(r'^(\d+)\s+(0x[0-9a-f]+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(.*)$', line.rstrip())
    if mm and mm.group(2).startswith('0x'):
        nm = mm.group(6)
        # 之前是按 latin-1 存的, 现在还原为 UTF-8 中文
        try: nm2 = nm.encode('latin-1').decode('utf-8')
        except Exception: nm2 = nm
        rows.append({'i': int(mm.group(1)), 'id18': int(mm.group(3)) if mm.group(3).isdigit() else None,
                     'name_raw': nm, 'name': nm2})
print('总行数: %d' % len(rows))
print('按 latin-1 去重: %d' % len(set(r['name_raw'] for r in rows)))
print('按 UTF-8 还原去重: %d' % len(set(r['name'] for r in rows)))
print('')
print('=== 前 80 个 ===')
for r in rows[:80]:
    print('    i=%-6d id18=%-8d %s' % (r['i'], r['id18'], r['name']))
print('')
print('=== 第 80..120 个 ===')
for r in rows[80:120]:
    print('    i=%-6d id18=%-8d %s' % (r['i'], r['id18'], r['name']))
print('')
print('=== 分段统计: 每个 id18 段里的名字 ===')
seg = {}
for r in rows:
    seg.setdefault(r['id18'], []).append(r)
print('id18 值个数: %d' % len(seg))
for k in sorted(seg, key=lambda x: min(y['i'] for y in seg[x]))[:6]:
    g = seg[k]
    print('    id18=%-8d 项数=%-6d 下标 %d..%d  名字样例: %s' % (k, len(g), g[0]['i'], g[-1]['i'], ', '.join(x['name'] for x in g[:4])))
print('    ...')
lastk = max(seg, key=lambda x: max(y['i'] for y in seg[x]))
g = seg[lastk]
print('    id18=%-8d 项数=%-6d 下标 %d..%d  名字样例: %s' % (lastk, len(g), g[0]['i'], g[-1]['i'], ', '.join(x['name'] for x in g[:4])))