import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
pid = fh.find_pid()
print('pid=%s' % pid, flush=True)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_exec_cmd.js', force_spawn=False)
print('fresh=%s' % fresh, flush=True)
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
print('=== 基准 setgamedate 510.6.7.0 ===', flush=True)
print('  ' + msg(e.exec('setgamedate', ['510.6.7.0'])), flush=True)
time.sleep(2)
print('  现在: ' + msg(e.exec('setgamedate', [])), flush=True)
tests = [
    ('addtimeforyears', ['10'],  '加 10 年  期望 520.6.7'),
    ('addtimeformonths', ['3'],  '加 3 月   期望 520.9.7'),
    ('addtimefordays', ['45'],   '加 45 天'),
    ('addtimeforhours', ['100'], '加 100 小时'),
    ('addtimefordays', ['-30'],  '减 30 天'),
    ('addtimeformonths', ['-5'], '减 5 月'),
    ('addtimeforyears', ['-3'],  '减 3 年'),
    ('addtimeforhours', ['-50'], '减 50 小时'),
]
for cmd, a, note in tests:
    print('=== %s %s   (%s) ===' % (cmd, a[0], note), flush=True)
    print('  ' + msg(e.exec(cmd, a)), flush=True)
    time.sleep(1.5)
    print('  现在: ' + msg(e.exec('setgamedate', [])), flush=True)
fh.detach(session)
