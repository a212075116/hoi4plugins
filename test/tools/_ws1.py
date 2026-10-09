import os, re
SD = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa/history/states'
files = {}
for fn in os.listdir(SD):
    m = re.match(r'^(\d+)-', fn)
    if m: files[int(m.group(1))] = fn
keep = set([7, 31, 423, 425, 426, 427, 430, 432, 433, 434, 435])
def info(sid):
    fn = files.get(sid)
    if not fn: return None
    t = open(os.path.join(SD, fn), encoding='utf-8-sig', errors='replace').read()
    mo = re.search(r'^\s*owner\s*=\s*([A-Za-z0-9_]+)', t, re.M)
    cat = re.search(r'state_category\s*=\s*(\w+)', t)
    prov = re.search(r'provinces\s*=\s*\{([^}]*)\}', t, re.S)
    nprov = len([x for x in prov.group(1).split() if x.isdigit()]) if prov else 0
    mp = re.search(r'^\s*manpower\s*=\s*(\d+)', t, re.M)
    bld = re.search(r'buildings\s*=\s*\{([^}]*)\}', t, re.S)
    nb = len([l for l in bld.group(1).splitlines() if l.strip()]) if bld else 0
    return (sid, mo.group(1) if mo else '?', cat.group(1) if cat else '?', nprov,
            int(mp.group(1)) if mp else 0, nb, len(t.splitlines()))
print('=== WS1 的 17 个州 (! = 保持 tag) ===')
ws1 = [2,5,7,8,11,12,14,15,17,18,20,24,26,29,31,35,49]
print('  %-4s %-6s %-12s %6s %10s %6s %6s' % ('id','owner','category','省份','manpower','建筑行','总行'))
for s in ws1:
    i = info(s)
    if i: print('  %-4d %-6s %-12s %6d %10d %6d %6d %s' % (i[0],i[1],i[2],i[3],i[4],i[5],i[6], '<<< 保持' if s in keep else ''))
print()
print('=== W00 的 10 个州 ===')
for s in [423,425,426,427,430,431,432,433,434,435]:
    i = info(s)
    if i: print('  %-4d %-6s %-12s %6d %10d %6d %6d %s' % (i[0],i[1],i[2],i[3],i[4],i[5],i[6], '<<< 保持' if s in keep else ''))
