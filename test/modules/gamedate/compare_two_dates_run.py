import sys, time, importlib.util as iu
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
s = iu.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = iu.module_from_spec(s); s.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/modules/gamedate/compare_two_dates.js', force_spawn=False)
e = sc.exports_sync
time.sleep(0.5)
print('=== 同一时刻两边对照 (每 4 秒) ===', flush=True)
for i in range(6):
    print('  T+%2ds  %s' % (i*4, e.both('0x28E4A003700')), flush=True)
    time.sleep(4)
fh.detach(session)
