import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_date.js', force_spawn=False)
e = sc.exports_sync
time.sleep(0.5)
B = 43800000          # 基准小时数
DAY0 = 182500         # 500.1.1 的天数
# 每月天数
MD = [31,28,31,30,31,30,31,31,30,31,30,31]
def days_of(y, m, d):
    return 365 * (y - 500) + sum(MD[:m-1]) + (d - 1)
def to_raw(y, m, d, h=0):
    return B + (DAY0 + days_of(y, m, d)) * 24 + h
print('写前: ' + e.getDate(), flush=True)
for (y, m, d) in [(510, 6, 7), (515, 3, 20), (500, 1, 1)]:
    raw = to_raw(y, m, d)
    print('--- 设置到 %d.%d.%d  raw=%d ---' % (y, m, d, raw), flush=True)
    print('  ' + e.setRaw(raw), flush=True)
    time.sleep(2)
    print('  读回: ' + e.getDate(), flush=True)
    print('  派生: ' + e.peek(0x478, 5), flush=True)
    time.sleep(4)
fh.detach(session)
