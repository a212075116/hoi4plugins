import sys, time, importlib.util as iu
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
s = iu.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
fh = iu.module_from_spec(s); s.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_exec_cmd.js', force_spawn=False)
e = sc.exports_sync
time.sleep(0.5)
def msg(r):
    for ln in str(r).split(chr(10)):
        if 'out->message' in ln: return ln.split('=',1)[1].strip()
    return '?'
b = msg(e.exec('setgamedate', []))
time.sleep(3)
a = msg(e.exec('setgamedate', []))
print('暂停前: %s -> %s  (%s)' % (b, a, 'running' if a != b else 'paused'), flush=True)
if a != b:
    print('  发送 auto_unpause -> ' + msg(e.exec('auto_unpause', ['2'])), flush=True)
    time.sleep(3)
    b2 = msg(e.exec('setgamedate', []))
    time.sleep(3)
    a2 = msg(e.exec('setgamedate', []))
    print('暂停后: %s -> %s  (%s)' % (b2, a2, 'running!' if a2 != b2 else 'paused OK'), flush=True)
fh.detach(session)
