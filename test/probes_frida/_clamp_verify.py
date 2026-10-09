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
def show(tag):
    lo, hi = lim()
    print('%-42s lo=%-6s hi=%-6s height=%.2f' % (tag, lo, hi, e.camHeight()))
def cmd(name, args, tag):
    r = str(e.exec(name, args))
    m = r.split('out->message=')[1].split(chr(10))[0].strip() if 'out->message' in r else r[:100]
    time.sleep(0.9)
    lo, hi = lim()
    print('%-42s lo=%-6s hi=%-6s height=%.2f' % (tag, lo, hi, e.camHeight()))
    print('      msg: ' + m)
print()
print('=== A. 指令: 设下限 1000, 当前 310 应被拉到 1000 ===')
cmd('setcamheight', ['310'], 'setcamheight 310 (复位)')
cmd('setcameraheight_lowerlimit', ['1000'], 'setcameraheight_lowerlimit 1000')
print()
print('=== B. 指令: 设上限 400, 高度应被拉到 400 ===')
cmd('setcameraheight_upperlimit', ['400'], 'setcameraheight_upperlimit 400')
print()
print('=== C. 复位上下限 ===')
cmd('setcameraheight_lowerlimit', ['50'], 'setcameraheight_lowerlimit 50')
cmd('setcameraheight_upperlimit', ['3000'], 'setcameraheight_upperlimit 3000')
cmd('setcamheight', ['310'], 'setcamheight 310')
print()
print('=== D. effect: 下限 1000 应把高度拉到 1000 ===')
r = str(e.exec('event', ['camtest.4']))
time.sleep(1.2)
lo, hi = lim()
print('%-42s lo=%-6s hi=%-6s height=%.2f' % ('camtest.4 (lower 1000)', lo, hi, e.camHeight()))
print()
print('=== E. effect: 上限 400 应把高度拉到 400 ===')
r = str(e.exec('event', ['camtest.5']))
time.sleep(1.2)
lo, hi = lim()
print('%-42s lo=%-6s hi=%-6s height=%.2f' % ('camtest.5 (upper 400)', lo, hi, e.camHeight()))
print()
print('=== 日志 ===')
lg = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/mod_loader_tbb.log'
for l in open(lg, encoding='utf-8', errors='replace').read().splitlines():
    if 'setcamlower' in l or 'setcamupper' in l or 'lowerlimit' in l or 'upperlimit' in l or '[eff] +' in l: print('  ' + l)
