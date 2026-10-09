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
    m = r.split('out->message=')[1].split(chr(10))[0].strip() if 'out->message' in r else r[:80]
    time.sleep(0.9)
    lo, hi = lim()
    print('%-40s lo=%-6s hi=%-6s h=%-9.2f %s' % (tag, lo, hi, e.camHeight(), m))
print()
print('== 真下限 = 35 ==')
cmd('setcameraheight_lowerlimit', ['0'],  'lower 0  -> 应夹到 35')
cmd('setcameraheight_lowerlimit', ['10'], 'lower 10 -> 应夹到 35')
cmd('setcameraheight_lowerlimit', ['35'], 'lower 35 -> 正好')
cmd('setcameraheight_lowerlimit', ['50'], 'lower 50 -> 正常')
print()
print('== tooltip 应显示夹紧后的值 ==')
cmd('setcameraheight_upperlimit', ['9000'], 'upper 9000 (真上限 3000)')
print()
print('== effect 侧 ==')
cmd('setcameraheight_lowerlimit', ['50'], 'lower 50')
cmd('setcameraheight_upperlimit', ['3000'], 'upper 3000')
for ev, tag in [('camtest.4','camtest.4 lower 1000'), ('camtest.5','camtest.5 upper 9000'), ('camtest.6','camtest.6 lower 0')]:
    try:
        e.exec('event', [ev])
    except Exception as ex:
        print('  %s exec 失败: %s' % (ev, ex)); break
    time.sleep(1.5)
    lo, hi = lim()
    print('%-40s lo=%-6s hi=%-6s h=%.2f' % ('  ' + tag, lo, hi, e.camHeight()))
print()
print('== 日志 ==')
lg = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/mod_loader_tbb.log'
for l in open(lg, encoding='utf-8', errors='replace').read().splitlines():
    if 'setcamlower' in l or 'setcamupper' in l or 'efftip' in l or 'true upper' in l or 'lowerlimit' in l or 'upperlimit' in l:
        print('  ' + l)
