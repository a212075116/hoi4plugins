import sys, time, importlib.util as iu
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
s = iu.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
fh = iu.module_from_spec(s); s.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_date.js', force_spawn=False)
d = sc.exports_sync
time.sleep(0.5)
print('raw : ' + d.getDate(), flush=True)
print('字段: ' + d.peek(0x478, 5), flush=True)
print('脏标志 +0x4C0: ' + d.peek(0x4C0, 1), flush=True)
fh.detach(session)
