import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_occ.js', force_spawn=False)
time.sleep(0.4)
e = sc.exports_sync
print(e.install())
print('=== 调用点所属函数符号 ===')
for r in (0xf919e4, 0xf99d8b, 0x24c8950):
    try: print('  rva=%#x -> %s' % (r, e.caller(r)))
    except Exception as ex: print('  rva=%#x ERR %s' % (r, str(ex)[:60]))
for i in range(20):
    time.sleep(3)
    print('  %ds: %s' % ((i+1)*3, e.stats()))
