import sys, time, importlib.util as iu
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
s = iu.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = iu.module_from_spec(s); s.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_hookfmt.js', force_spawn=False)
print('fresh=%s' % fresh, flush=True)
e = sc.exports_sync
time.sleep(0.5)
print(e.install(), flush=True)
print('等 15 秒 (游戏当前应处于暂停)...', flush=True)
time.sleep(15)
print('计数: %s' % e.n(), flush=True)
print(e.dump(), flush=True)
fh.detach(session)
