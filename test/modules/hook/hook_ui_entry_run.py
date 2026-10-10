import sys, time, importlib.util as iu
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
s = iu.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = iu.module_from_spec(s); s.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/modules/hook/hook_ui_entry.js', force_spawn=False)
print('fresh=%s' % fresh, flush=True)
e = sc.exports_sync
time.sleep(0.5)
print(e.install(), flush=True)
print('等 12 秒 (游戏当前在跑)...', flush=True)
time.sleep(12)
print('调用次数 = %d' % e.n(), flush=True)
print(e.dump(), flush=True)
fh.detach(session)
