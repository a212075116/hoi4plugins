import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/exec_console_command.js', force_spawn=False)
e = sc.exports_sync
time.sleep(0.5)
def msg(r):
    for ln in str(r).split(chr(10)):
        if 'out->message' in ln: return ln.split('=',1)[1].strip()
    return '?'
print('写前: ' + msg(e.exec('setgamedate', [])), flush=True)
print('设 510.6.7.0: ' + msg(e.exec('setgamedate', ['510.6.7.0'])), flush=True)
time.sleep(2)
print('T+2s : ' + msg(e.exec('setgamedate', [])), flush=True)
time.sleep(6)
print('T+8s : ' + msg(e.exec('setgamedate', [])), flush=True)
print('设 515.3.20.0: ' + msg(e.exec('setgamedate', ['515.3.20.0'])), flush=True)
time.sleep(4)
print('T+12s: ' + msg(e.exec('setgamedate', [])), flush=True)
fh.detach(session)
