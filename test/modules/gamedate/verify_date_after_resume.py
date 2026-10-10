import sys, time, importlib.util as iu
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
def load(n, p):
    s = iu.spec_from_file_location(n, p); m = iu.module_from_spec(s); s.loader.exec_module(m); return m
fh = load('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/exec_console_command.js', force_spawn=False)
e = sc.exports_sync
time.sleep(0.5)
def msg(r):
    for ln in str(r).split(chr(10)):
        if 'out->message' in ln: return ln.split('=',1)[1].strip()
    return '?'
print('设基准 510.6.7.0: ' + msg(e.exec('setgamedate', ['510.6.7.0'])), flush=True)
print('auto_unpause 3  : ' + msg(e.exec('auto_unpause', ['3'])), flush=True)
print('gamespeed 3     : ' + msg(e.exec('gamespeed', ['3'])), flush=True)
for i in range(4):
    time.sleep(4)
    print('  T+%2ds 日期: %s' % ((i+1)*4, msg(e.exec('setgamedate', []))), flush=True)
print('加 100 天: ' + msg(e.exec('addtimefordays', ['100'])), flush=True)
for i in range(2):
    time.sleep(4)
    print('  T+%2ds 日期: %s' % ((i+1)*4, msg(e.exec('setgamedate', []))), flush=True)
fh.detach(session)
