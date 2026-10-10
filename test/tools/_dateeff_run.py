import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
pid = fh.find_pid()
print('pid=%s' % pid, flush=True)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/exec_console_command.js', force_spawn=False)
e = sc.exports_sync
time.sleep(0.5)
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
def msg(r):
    for ln in str(r).split(chr(10)):
        if 'out->message' in ln: return ln.split('=',1)[1].strip()
    return '?'
e.exec('auto_unpause', ['3'])
time.sleep(8)
print('触发前: ' + msg(e.exec('setgamedate', [])), flush=True)
for ev in ['zzdatetest.1', 'zzdatetest.2', 'zzdatetest.3']:
    print('=== event %s ===' % ev, flush=True)
    print('  ' + msg(e.exec('event', [ev])), flush=True)
    time.sleep(4)
    print('  现在: ' + msg(e.exec('setgamedate', [])), flush=True)
fh.detach(session)
