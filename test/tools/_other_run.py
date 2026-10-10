import sys, time, importlib.util as iu
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
s = iu.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
fh = iu.module_from_spec(s); s.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_other.js', force_spawn=False)
e = sc.exports_sync
time.sleep(0.5)
gs = e.gs()
print('CGameState = ' + gs, flush=True)
print('我那个(年) = 0x' + format(int(gs, 16) + 0x478, 'x'), flush=True)
print(flush=True)
print('=== 你找到的 0x28E4A003700 附近 ===', flush=True)
try:
    print(e.around('0x28E4A003700', 0x40, 0x40), flush=True)
except Exception as ex:
    print('  ERR: %s' % ex, flush=True)
print(flush=True)
print('=== 它的首 qword (虚表?) ===', flush=True)
try:
    print('  ' + e.vtOf('0x28E4A003700'), flush=True)
except Exception as ex:
    print('  ERR: %s' % ex, flush=True)
fh.detach(session)
