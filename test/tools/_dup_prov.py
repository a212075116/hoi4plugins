import os, re, collections
SD = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa/history/states'
owner_of = {}
dups = collections.defaultdict(list)
nstate = 0
for fn in sorted(os.listdir(SD)):
    p = os.path.join(SD, fn)
    try: t = open(p, encoding='utf-8-sig', errors='replace').read()
    except Exception: continue
    mid = re.search(r'^\s*id\s*=\s*(\d+)', t, re.M)
    if not mid: continue
    sid = int(mid.group(1)); nstate += 1
    mp = re.search(r'provinces\s*=\s*\{([^}]*)\}', t, re.S)
    if not mp:
        dups['(无 provinces 块)'].append(sid); continue
    for tok in mp.group(1).split():
        if not tok.isdigit(): continue
        pv = int(tok)
        if pv in owner_of:
            dups[pv].append((sid, owner_of[pv]))
        else:
            owner_of[pv] = sid
print('state 数: %d   被引用的省份数: %d' % (nstate, len(owner_of)))
real = {k: v for k, v in dups.items() if isinstance(k, int)}
print('重复声明的省份数: %d' % len(real))
print()
if real:
    print('=== 重复省份 (前 25, 格式: 省 -> [州A(首次), 州B]) ===')
    for pv in sorted(real)[:25]:
        first = owner_of[pv]
        others = [x[0] for x in real[pv]]
        print('  省 %-6d 首次在州 %-4d 又出现在 %s' % (pv, first, others))
    # 检查那 11 个保持 tag 的州是否与重复相关
    keep = [7, 31, 423, 425, 426, 427, 430, 432, 433, 434, 435]
    print()
    print('=== 11 个保持 tag 的州涉及的省份 ===')
    for fn in sorted(os.listdir(SD)):
        m = re.match(r'^(\d+)-', fn)
        if not m or int(m.group(1)) not in keep: continue
        sid = int(m.group(1))
        t = open(os.path.join(SD, fn), encoding='utf-8-sig', errors='replace').read()
        mp = re.search(r'provinces\s*=\s*\{([^}]*)\}', t, re.S)
        pvs = [int(x) for x in mp.group(1).split() if x.isdigit()] if mp else []
        d = [x for x in pvs if x in real or x in owner_of and owner_of[x] != sid]
        print('  州 %-4d 省份 %s   其中冲突: %s' % (sid, pvs[:6], d[:6]))
