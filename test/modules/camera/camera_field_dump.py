import sys, importlib.util as iu, time
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
s = iu.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = iu.module_from_spec(s); s.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/modules/camera/camera_field_dump.js', force_spawn=False)
e = sc.exports_sync
time.sleep(0.5)
print('=== 当前摄像机字段 ===', flush=True)
print(e.dump(), flush=True)
fh.detach(session)
