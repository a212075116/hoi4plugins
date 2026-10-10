import sys, time, importlib.util as iu
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
def load(name, path):
    s = iu.spec_from_file_location(name, path)
    m = iu.module_from_spec(s); s.loader.exec_module(m); return m
fh = load('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/exec_console_command.js', force_spawn=False)
e = sc.exports_sync
time.sleep(0.5)
def msg(r):
    for ln in str(r).split(chr(10)):
        if 'out->message' in ln: return ln.split('=',1)[1].strip()
    return '?'
print('=== 暂停状态下设 510.6.7.0 ===', flush=True)
print('  ' + msg(e.exec('setgamedate', ['510.6.7.0'])), flush=True)
time.sleep(2)
print('  立刻回显: ' + msg(e.exec('setgamedate', [])), flush=True)
fh.detach(session)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/modules/gamedate/game_date_read.js', force_spawn=False)
d = sc.exports_sync
time.sleep(0.5)
print('  raw   : ' + d.getDate(), flush=True)
print('  派生  : ' + d.peek(0x478, 5), flush=True)
print('          (+0x478年 +0x47c本月天数 +0x480日 +0x484年内第几天 +0x488月-1)', flush=True)
print(flush=True)
print('=== 再设 515.3.20.0 ===', flush=True)
fh.detach(session)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/exec_console_command.js', force_spawn=False)
e = sc.exports_sync
time.sleep(0.5)
print('  ' + msg(e.exec('setgamedate', ['515.3.20.0'])), flush=True)
fh.detach(session)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/modules/gamedate/game_date_read.js', force_spawn=False)
d = sc.exports_sync
time.sleep(0.5)
print('  派生  : ' + d.peek(0x478, 5), flush=True)
print('=== 加减: addtimefordays 45 ===', flush=True)
fh.detach(session)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/exec_console_command.js', force_spawn=False)
e = sc.exports_sync
time.sleep(0.5)
print('  ' + msg(e.exec('addtimefordays', ['45'])), flush=True)
fh.detach(session)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/modules/gamedate/game_date_read.js', force_spawn=False)
d = sc.exports_sync
time.sleep(0.5)
print('  派生  : ' + d.peek(0x478, 5), flush=True)
fh.detach(session)
