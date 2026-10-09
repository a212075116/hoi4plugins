import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
fh.set_start_tag('ABY')
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_exec_cmd.js', force_spawn=True, wait=False)
print('pid=%s' % pid, flush=True)
e = sc.exports_sync
time.sleep(0.5)
# 自己轮询 CGameState, 不依赖可能卡住的 wait_in_game
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
print('CGameState=%s  用时 %.0fs' % (gs, time.time()-t0), flush=True)
if gs:
    r = e.exec('auto_unpause', ['3'])
    for ln in str(r).split(chr(10)):
        if 'out->message' in ln: print('  ' + ln.strip(), flush=True)
print('READY', flush=True)
