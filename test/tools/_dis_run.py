import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_dis.js', force_spawn=False)
time.sleep(0.5)
e = sc.exports_sync
for rva, tag in [(0x15fb70,'CGameDate[0]'), (0x15bfd8,'CGameDate[6]'), (0x1608c0,'CGameDate[16]'), (0x1aaea0,'CGameDate[18]'), (0x545e20,'CGameDate[19]')]:
    print('=== %s  rva=%#x (%d 条) ===' % (tag, rva, 18))
    print(e.dis(rva, 18))
    print()
