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
def limits():
    s = e.camLimits()
    d = {}
    for line in s.split(chr(10)):
        p = line.split()
        if len(p) >= 3:
            d[p[0]] = p[1].split('=')[1]
    return d.get('+0x6d0'), d.get('+0x6d4')
def show(tag):
    lo, hi = limits()
    print('%-34s  lo=%-6s hi=%-6s  height=%.2f' % (tag, lo, hi, e.camHeight()))
print()
show('初始')
print()
print('--- 指令 ---')
r = str(e.exec('setcameraheight_lowerlimit', ['100']))
print('  setcameraheight_lowerlimit 100 -> ' + r.split('out->message=')[1].split(chr(10))[0].strip() if 'out->message' in r else r[:120])
time.sleep(0.5); show('  之后')
r = str(e.exec('setcameraheight_upperlimit', ['2000']))
print('  setcameraheight_upperlimit 2000 -> ' + r.split('out->message=')[1].split(chr(10))[0].strip() if 'out->message' in r else r[:120])
time.sleep(0.5); show('  之后')
print()
print('--- 验证上限生效: setcamheight 5000 应被夹到 2000 ---')
r = str(e.exec('setcamheight', ['5000']))
time.sleep(0.8); show('  setcamheight 5000')
print()
print('--- 验证下限生效: setcamheight 10 应被夹到 100 ---')
r = str(e.exec('setcamheight', ['10']))
time.sleep(0.8); show('  setcamheight 10')
print()
print('--- effect ---')
for ev, desc in [('camtest.1','set height 1500'), ('camtest.4','set lower 300'),
                 ('camtest.5','set upper 2500'), ('camtest.6','change -300')]:
    r = str(e.exec('event', [ev]))
    time.sleep(1.2)
    show('  %s (%s)' % (ev, desc))
print()
print('=== 日志 ===')
lg = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/mod_loader_tbb.log'
for l in open(lg, encoding='utf-8', errors='replace').read().splitlines():
    if 'efftip' in l or '[eff] ' in l and '#' in l or 'setcamlower' in l or 'setcamupper' in l or 'lowerlimit' in l or 'upperlimit' in l or 'change_camera' in l: print('  ' + l)
