import sys, time, importlib.util as iu
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
spec = iu.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
fh = iu.module_from_spec(spec); spec.loader.exec_module(fh)
pid = fh.find_pid()
print('pid=%s' % pid, flush=True)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_exec_cmd.js', force_spawn=False)
e = sc.exports_sync
time.sleep(0.5)
def msg(r):
    for ln in str(r).split(chr(10)):
        if 'out->message' in ln: return ln.split('=',1)[1].strip()
    return '?'
# 等 CGameState 建立
GS_JS = 'rpc.exports={gs:function(){var b=Process.getModuleByName("hoi4.exe").base.add(0x332F260).readPointer();return b.isNull()?null:b.toString();}};'
gsc = session.create_script(GS_JS)
gsc.load()
t0 = time.time()
while time.time() - t0 < 120:
    try:
        gs = gsc.exports_sync.gs()
        if gs: break
    except Exception: pass
    time.sleep(1)
print('CGameState=%s (%.0fs)' % (gs, time.time()-t0), flush=True)
print('等 20 秒让它初始化完(不发 auto_unpause, 保持暂停)...', flush=True)
time.sleep(20)
print('当前(应仍是暂停): ' + msg(e.exec('setgamedate', [])), flush=True)
fh.detach(session)
# 读派生字段
spec2 = iu.spec_from_file_location('fh2', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
fh2 = iu.module_from_spec(spec2); spec2.loader.exec_module(fh2)
pid, session, sc, fresh = fh2.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_date.js', force_spawn=False)
d = sc.exports_sync
time.sleep(0.5)
print('--- 写前 raw + 派生 ---', flush=True)
print('  raw: ' + d.getDate(), flush=True)
print('  ' + d.peek(0x478, 5), flush=True)
fh2.detach(session)
