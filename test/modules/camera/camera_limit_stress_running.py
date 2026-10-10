import sys, importlib.util as iu, time, math, re
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
s = iu.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = iu.module_from_spec(s); s.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/exec_console_command.js', force_spawn=False)
e = sc.exports_sync
time.sleep(0.5)
def full():
    return e.camLimits()
def check(label):
    c = e.cam()
    bad = []
    for m in re.finditer(r'(\+0x[0-9A-Fa-f]+)\([^)]*\)=([-+0-9.eE]+)', c):
        try:
            f = float(m.group(2))
            if math.isnan(f): bad.append(m.group(1) + '=NaN')
            elif math.isinf(f): bad.append(m.group(1) + '=Inf')
        except: pass
    print('  %-40s %s%s' % (label, c, ('   ★★★ ' + ', '.join(bad)) if bad else '   OK'), flush=True)
    return bad
print('=== 先让游戏跑起来 ===', flush=True)
print(e.exec('auto_unpause', []), flush=True)
print(e.exec('gamespeed', ['5']), flush=True)
time.sleep(3)
print(e.exec('auto_unpause', []), flush=True)
time.sleep(2)
check('跑动后基线')
print('', flush=True)
print('=== 跑动状态下改上下限 ===', flush=True)
cases = [
    ('setcameraheight_upperlimit', '1',    'upper=1'),
    ('setcameraheight_lowerlimit', '1',    'lower=1'),
    ('setcameraheight_upperlimit', '2',    'upper=2 (区间极小)'),
    ('setcamheight', '1',                  'height=1'),
    ('setcamheight', '3000',               'height=3000'),
    ('setcameraheight_lowerlimit', '2999', 'lower=2999'),
    ('setcameraheight_upperlimit', '3000', 'upper=3000 (区间仅 1)'),
    ('setcameraheight_lowerlimit', '0',    'lower=0'),
    ('setcameraheight_upperlimit', '99999','upper=99999'),
]
hits = []
for cmd, arg, label in cases:
    e.exec(cmd, [arg])
    time.sleep(1.0)
    if check(label): hits.append(label)
print('', flush=True)
print('=== 命中: %d ===' % len(hits), flush=True)
for h in hits: print('  ' + h, flush=True)
fh.detach(session)
