import os, re
SD = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa/history/states'
n = 0
owner_in_core = 0
owner_not_in_core = []
no_owner = []
for fn in sorted(os.listdir(SD)):
    p = os.path.join(SD, fn)
    try: t = open(p, encoding='utf-8-sig', errors='replace').read()
    except Exception: continue
    n += 1
    mo = re.search(r'^\s*owner\s*=\s*([A-Za-z0-9_]+)', t, re.M)
    if not mo:
        no_owner.append(fn); continue
    owner = mo.group(1)
    cores = re.findall(r'add_core_of\s*=\s*([A-Za-z0-9_]+)', t)
    if owner in cores:
        owner_in_core += 1
    else:
        owner_not_in_core.append((fn, owner, cores))
print('state 文件: %d' % n)
print('owner 在 core 列表里: %d' % owner_in_core)
print('owner 不在 core 列表里: %d' % len(owner_not_in_core))
print('无 owner: %d' % len(no_owner))
print()
if owner_not_in_core:
    print('=== owner 不在 core 里的 state (前 25) ===')
    for fn, o, c in owner_not_in_core[:25]:
        print('  %-32s owner=%-5s cores=%s' % (fn, o, ','.join(c[:6]) if c else '(空)'))
else:
    print('(全部 owner 都在 core 列表里)')
