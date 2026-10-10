import sys, importlib.util as iu, time, math, re
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
s = iu.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = iu.module_from_spec(s); s.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/exec_console_command.js', force_spawn=False)
e = sc.exports_sync
time.sleep(0.5)

def report(label):
    c = e.camLimits()
    bad = []
    vals = {}
    for m in re.finditer(r'\+0x([0-9A-Fa-f]+)\s+u32=(\d+)\s+i32=(-?\d+)\s+f32=([-+0-9.eE]+)', c):
        off = int(m.group(1), 16)
        vals[off] = (m.group(2), m.group(3), m.group(4))
        try:
            fv = float(m.group(4))
            if math.isnan(fv): bad.append('+0x%X=NaN' % off)
            elif math.isinf(fv): bad.append('+0x%X=Inf' % off)
        except: pass
    tgt = vals.get(0x69C, ('?','?','?'))
    cur = vals.get(0x678, ('?','?','?'))
    lo  = vals.get(0x6D0, ('?','?','?'))
    hi  = vals.get(0x6D4, ('?','?','?'))
    print('  %-26s 目标=%-9s 当前=%-9s 下限=%-8s 上限=%-8s %s' % (
        label, tgt[2], cur[2], lo[2], hi[2], ('★ ' + ','.join(bad)) if bad else 'OK'), flush=True)
    return bad

print('=== effect 路径 (事件触发) ===', flush=True)
hits = report('基线') and ['基线'] or []
seq = [
    ('zzdatetest.20', 'eff lower=100'),
    ('zzdatetest.21', 'eff upper=200'),
    ('zzdatetest.22', 'eff upper=4000  <== 关键'),
    ('zzdatetest.23', 'eff lower=50'),
    ('zzdatetest.24', 'eff height=800'),
    ('zzdatetest.25', 'eff add -700'),
]
for ev, label in seq:
    r = e.exec('event', [ev])
    time.sleep(1.5)
    if report(label): hits.append(label)
print('', flush=True)
print('=== 命中 NaN/Inf: %d ===' % len(hits), flush=True)
for h in hits: print('  ' + h, flush=True)
fh.detach(session)
