import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
pid = fh.find_pid()
print('attach pid=%s' % pid, flush=True)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_exec_cmd.js', force_spawn=False)
print('fresh=%s (必须是 False)' % fresh, flush=True)
e = sc.exports_sync
time.sleep(0.5)
# 等 CGameState
import json
GS_JS = 'rpc.exports={gs:function(){var b=Process.getModuleByName("hoi4.exe").base.add(0x332F260).readPointer();return b.isNull()?null:b.toString();}};'
gsc = session.create_script(GS_JS)
gsc.load()
t0 = time.time()
gs = None
while time.time() - t0 < 120:
    try:
        gs = gsc.exports_sync.gs()
        if gs: break
    except Exception: pass
    time.sleep(1)
print('CGameState=%s (%.0fs)' % (gs, time.time()-t0), flush=True)
print('=== auto_unpause 3 ===', flush=True)
e.exec('auto_unpause', ['3'])
print(flush=True)
print('=== 1) 无参回显: setgamedate ===', flush=True)
print(e.exec('setgamedate', []), flush=True)
time.sleep(1)
print('=== 2) 设 510.6.7.0 ===', flush=True)
print(e.exec('setgamedate', ['510.6.7.0']), flush=True)
time.sleep(3)
print('=== 3) 再回显 ===', flush=True)
print(e.exec('setgamedate', []), flush=True)
fh.detach(session)
