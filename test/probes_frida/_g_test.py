import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/exec_console_command.js', force_spawn=False)
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
def st(tag):
    try:
        lo, hi = lim()
        h = e.camHeight()
        print('  %-34s lo=%-6s hi=%-6s h=%.2f' % (tag, lo, hi, h))
    except Exception as ex:
        print('  %-34s 读取失败: %s' % (tag, ex))
st('初始')
print()
print('--- 单个 effect: camtest.4 (lower 1000) ---')
try:
    r = str(e.exec('event', ['camtest.4']))
    print('  exec: ' + r.replace(chr(10), ' ')[:110])
except Exception as ex:
    print('  exec 失败: ' + str(ex))
time.sleep(1.5)
st('camtest.4 之后')
print()
print('--- 单个 effect: camtest.5 (upper 9000) ---')
try:
    r = str(e.exec('event', ['camtest.5']))
    print('  exec: ' + r.replace(chr(10), ' ')[:110])
except Exception as ex:
    print('  exec 失败: ' + str(ex))
time.sleep(1.5)
st('camtest.5 之后')
print()
print('=== 日志 ===')
lg = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/mod_loader_tbb.log'
for l in open(lg, encoding='utf-8', errors='replace').read().splitlines()[-16:]: print('  ' + l)
