import sys, time, importlib.util as iu
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
s = iu.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = iu.module_from_spec(s); s.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/modules/gamedate/memory_around_address.js', force_spawn=False)
e = sc.exports_sync
time.sleep(0.5)
ADDR = '0x28E4A003700'
def snap(tag):
    print('--- %s ---' % tag, flush=True)
    print('  ' + e.around(ADDR, 0x60, 0x60), flush=True)
snap('T0')
time.sleep(8)
snap('T+8s')
fh.detach(session)
