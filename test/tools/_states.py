import os, re, collections
SD = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa/history/states'
CD = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa/common/countries'
HD = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa/history/countries'
files = sorted(os.listdir(SD))
print('state 文件数: %d' % len(files))
owners = collections.Counter()
ctrl = collections.Counter()
n_owner = 0
n_ctrl = 0
no_owner = []
for fn in files:
    p = os.path.join(SD, fn)
    try:
        t = open(p, encoding='utf-8-sig', errors='replace').read()
    except Exception:
        continue
    mo = re.search(r'^\s*owner\s*=\s*([A-Za-z0-9_]+)', t, re.M)
    mc = re.search(r'^\s*controller\s*=\s*([A-Za-z0-9_]+)', t, re.M)
    if mo:
        owners[mo.group(1)] += 1; n_owner += 1
    else:
        no_owner.append(fn)
    if mc:
        ctrl[mc.group(1)] += 1; n_ctrl += 1
print('有 owner 的: %d   有 controller 的: %d   无 owner: %d' % (n_owner, n_ctrl, len(no_owner)))
print()
print('=== owner 分布 (前 30) ===')
for k, v in owners.most_common(30):
    print('  %-8s %d' % (k, v))
print()
print('=== 无 owner 的 state 文件 (前 15) ===')
for f in no_owner[:15]:
    print('  ' + f)
print()
# mod 定义了哪些 country tag
tags = set()
for fn in os.listdir(CD):
    tags.add(fn.split('-')[0].strip())
ct = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa/common/country_tags'
if os.path.isdir(ct):
    for fn in os.listdir(ct):
        try:
            for line in open(os.path.join(ct, fn), encoding='utf-8-sig', errors='replace'):
                m = re.match(r'\s*([A-Z0-9]{3})\s*=', line)
                if m: tags.add(m.group(1))
        except Exception: pass
print('=== mod 定义的 tag 数: %d ===' % len(tags))
unk = [k for k in owners if k not in tags]
print('=== owner 里不在 mod tag 列表中的 (%d) ===' % len(unk))
for k in unk[:20]: print('  ' + k)
