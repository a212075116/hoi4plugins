import sys, importlib.util as iu, time, math, re
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
s = iu.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = iu.module_from_spec(s); s.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/exec_console_command.js', force_spawn=False)
e = sc.exports_sync
time.sleep(0.5)

def num(s):
    m = re.search(r'=([-+0-9.eE]+)', s)
    try: return float(m.group(1))
    except: return float('nan')

def state():
    c = e.cam()
    parts = dict(re.findall(r'(\+0x[0-9A-Fa-f]+\([^)]*\))=([-+0-9.eE]+)', c))
    return c, parts

def check(label):
    c, p = state()
    bad = []
    for k, v in p.items():
        try:
            f = float(v)
            if math.isnan(f): bad.append(k + '=NaN')
            elif math.isinf(f): bad.append(k + '=Inf')
        except: pass
    tag = ('   ★★★ ' + ', '.join(bad)) if bad else '   OK'
    print('  %-42s %s%s' % (label, c, tag), flush=True)
    return bad

print('=== 摄像机上下限压力测试 (单会话) ===', flush=True)
check('基线')

cases = [
    ('setcameraheight_lowerlimit', '4000', 'lower=4000 (与 upper 相等)'),
    ('setcameraheight_lowerlimit', '3000', 'lower=3000'),
    ('setcameraheight_upperlimit', '100',  'upper=100'),
    ('setcameraheight_upperlimit', '50',   'upper=50 (与 lower 相等)'),
    ('setcameraheight_lowerlimit', '35',   'lower=35'),
    ('setcameraheight_upperlimit', '1',    'upper=1 (极小)'),
    ('setcameraheight_lowerlimit', '5000', 'lower=5000 (超大, 应被钳)'),
    ('setcameraheight_upperlimit', '100000', 'upper=100000 (超大, 应被钳)'),
    ('setcameraheight_lowerlimit', '50',   'lower=50 (恢复)'),
    ('setcameraheight_upperlimit', '4000', 'upper=4000 (恢复)'),
]
hits = []
for cmd, arg, label in cases:
    r = e.exec(cmd, [arg])
    time.sleep(1.0)
    if check(label): hits.append(label)

print('', flush=True)
print('=== 命中 NaN/Inf 的用例: %d ===' % len(hits), flush=True)
for h in hits: print('  ' + h, flush=True)
fh.detach(session)
