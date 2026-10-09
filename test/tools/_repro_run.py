import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_date.js', force_spawn=False)
e = sc.exports_sync
time.sleep(0.5)
B = 43800000
DAY0 = 182500
MD = [31,28,31,30,31,30,31,31,30,31,30,31]
def to_raw(y, m, d, h=0):
    return B + (DAY0 + 365*(y-500) + sum(MD[:m-1]) + (d-1)) * 24 + h
print('当前: ' + e.getDate(), flush=True)
for i, (y, m, d) in enumerate([(510,6,7), (515,3,20), (500,1,1)], 1):
    raw = to_raw(y, m, d)
    print('--- 第 %d 次: 目标 %d.%d.%d  raw=%d ---' % (i, y, m, d, raw), flush=True)
    try:
        print('  write: ' + e.setRaw(raw), flush=True)
    except Exception as ex:
        print('  ★ 写入时异常: %s' % ex, flush=True); break
    time.sleep(2)
    try:
        print('  读回: ' + e.getDate(), flush=True)
        print('  派生: ' + e.peek(0x478, 5), flush=True)
    except Exception as ex:
        print('  ★ 读回时异常: %s' % ex, flush=True); break
    time.sleep(4)
print('DONE', flush=True)
