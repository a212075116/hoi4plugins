import os, re, collections
SD = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa/history/states'
by_owner = collections.defaultdict(list)
noccore = collections.defaultdict(list)
for fn in sorted(os.listdir(SD)):
    m = re.match(r'^(\d+)-', fn)
    if not m: continue
    sid = int(m.group(1))
    t = open(os.path.join(SD, fn), encoding='utf-8-sig', errors='replace').read()
    mo = re.search(r'^\s*owner\s*=\s*([A-Za-z0-9_]+)', t, re.M)
    if not mo: continue
    o = mo.group(1)
    by_owner[o].append(sid)
    if not re.search(r'add_core_of', t):
        noccore[o].append(sid)
print('owner 种类: %d' % len(by_owner))
print()
print('=== owner=W00 (MapUtilities) ===')
print('  全部州: ' + str(by_owner.get('W00', [])))
print('  其中无 core 的: ' + str(noccore.get('W00', [])))
print()
print('=== owner=WS1 (SnowlandNorth) ===')
print('  全部州: ' + str(by_owner.get('WS1', [])))
print('  其中无 core 的: ' + str(noccore.get('WS1', [])))
print()
print('=== 其它 W* 国家 ===')
for k in sorted(by_owner):
    if k.startswith('W') and k != 'W00':
        print('  %-5s 全部=%s' % (k, by_owner[k]))
print()
print('=== 无 core 的州总数按 owner 分组 ===')
for k in sorted(noccore, key=lambda x: -len(noccore[x])):
    print('  %-6s %d 个: %s' % (k, len(noccore[k]), noccore[k][:12]))
print()
keep = [7, 31, 423, 425, 426, 427, 430, 432, 433, 434, 435]
print('=== 11 个保持 tag 的州的 owner ===')
for s in keep:
    for k, v in by_owner.items():
        if s in v: print('  id=%-4d owner=%s' % (s, k)); break
