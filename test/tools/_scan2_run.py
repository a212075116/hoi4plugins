import sys, time, importlib.util as iu
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
s = iu.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
fh = iu.module_from_spec(s); s.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_scan2.js', force_spawn=False)
e = sc.exports_sync
time.sleep(0.5)
print('=== CGameState+0x460..0x520 (看两个 CGameDate 对象) ===', flush=True)
print('  ' + e.peek(0x460, 48), flush=True)
print(flush=True)
print('=== CGameState+0x4a0..0x4e0 ===', flush=True)
print('  ' + e.peek(0x4a0, 16), flush=True)
fh.detach(session)
