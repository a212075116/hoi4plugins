import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_hex.js', force_spawn=False)
time.sleep(0.4)
e = sc.exports_sync
for base in (0x297e520, 0x297e530, 0x297e537):
    print('%#x : %r' % (base, e.txt(base, 64)))
    print('        bytes: ' + e.hex(base, 16))
