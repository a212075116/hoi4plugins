import sys, time, importlib.util as iu
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
s = iu.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = iu.module_from_spec(s); s.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_finda1.js', force_spawn=False)
e = sc.exports_sync
time.sleep(0.5)
print(e.install(), flush=True)
time.sleep(3)
a1 = e.a1()
print('a1 = %s' % a1, flush=True)
print('扫指向它的 qword (最多 20):', flush=True)
print(e.ptrsToA1(20), flush=True)
fh.detach(session)
