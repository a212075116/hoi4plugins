import sys, time, importlib.util as iu
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
s = iu.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = iu.module_from_spec(s); s.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/exec_console_command.js', force_spawn=False)
e = sc.exports_sync
time.sleep(0.5)
def msg(r):
    for ln in str(r).split(chr(10)):
        if 'out->message' in ln: return ln.split('=',1)[1].strip()
    return '?'
print('gamespeed 5 -> ' + msg(e.exec('gamespeed', ['5'])), flush=True)
for attempt in range(4):
    before = msg(e.exec('setgamedate', []))
    time.sleep(3)
    after = msg(e.exec('setgamedate', []))
    print('  尝试%d: %s -> %s' % (attempt+1, before, after), flush=True)
    if before != after:
        print('  ✓ 日期在走', flush=True)
        break
    print('  auto_unpause 2 -> ' + msg(e.exec('auto_unpause', ['2'])), flush=True)
time.sleep(2)
print('最终: ' + msg(e.exec('setgamedate', [])), flush=True)
fh.detach(session)
