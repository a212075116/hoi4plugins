import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_exec_cmd.js', force_spawn=False)
time.sleep(0.3)
e = sc.exports_sync
t0 = time.time()
while time.time() - t0 < 180:
    if e.ready().get('ok'): break
    time.sleep(0.5)
print('进地图 %.1f 秒' % (time.time()-t0))
def lim():
    d = {}
    for line in e.camLimits().split(chr(10)):
        p = line.split()
        if len(p) >= 3: d[p[0]] = p[1].split('=')[1]
    return d.get('+0x6d0'), d.get('+0x6d4')
def cmd(name, args, tag):
    r = str(e.exec(name, args))
    m = r.split('out->message=')[1].split(chr(10))[0].strip() if 'out->message' in r else r[:90]
    time.sleep(0.9)
    lo, hi = lim()
    print('%-40s lo=%-6s hi=%-6s h=%-9.2f  %s' % (tag, lo, hi, e.camHeight(), m))
print()
print('=== A. 复位 ===')
cmd('setcameraheight_lowerlimit', ['50'], 'lower 50')
cmd('setcameraheight_upperlimit', ['3000'], 'upper 3000')
cmd('setcamheight', ['310'], 'height 310')
print()
print('=== B. 夹紧行为 (当前 310 设下限 1000) ===')
cmd('setcameraheight_lowerlimit', ['1000'], 'lower 1000')
print()
print('=== C. 真上限: 上限设 9000 应被夹到 3000 ===')
cmd('setcameraheight_upperlimit', ['9000'], 'upper 9000')
print()
print('=== D. 真下限: 下限设 0 应被夹到 1 ===')
cmd('setcameraheight_lowerlimit', ['0'], 'lower 0')
cmd('setcameraheight_lowerlimit', ['-5'], 'lower -5')
print()
print('=== E. 下限 > 上限 -> 上限 = 下限 ===')
cmd('setcameraheight_lowerlimit', ['1500'], 'lower 1500 (hi 应跟着变 1500)')
print()
print('=== F. 复位 ===')
cmd('setcameraheight_lowerlimit', ['50'], 'lower 50')
cmd('setcameraheight_upperlimit', ['3000'], 'upper 3000')
cmd('setcamheight', ['310'], 'height 310')
print()
print('=== G. effect 侧 ===')
cmd('setcameraheight_lowerlimit', ['50'], 'lower 50')
for ev, tag in [('camtest.4','camtest.4 lower 1000'), ('camtest.5','camtest.5 upper 9000')]:
    r = str(e.exec('event', [ev]))
    time.sleep(1.2)
    lo, hi = lim()
    print('%-40s lo=%-6s hi=%-6s h=%-9.2f' % (tag, lo, hi, e.camHeight()))
print()
print('=== 日志 ===')
lg = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/mod_loader_tbb.log'
for l in open(lg, encoding='utf-8', errors='replace').read().splitlines():
    if 'setcamlower' in l or 'setcamupper' in l or 'true upper' in l or 'lowerlimit' in l or 'upperlimit' in l: print('  ' + l)
