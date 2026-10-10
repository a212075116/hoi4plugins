import sys, time, importlib.util as iu
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
spec = iu.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = iu.module_from_spec(spec); spec.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/exec_console_command.js', force_spawn=False)
e = sc.exports_sync
time.sleep(0.5)
def msg(r):
    for ln in str(r).split(chr(10)):
        if 'out->message' in ln: return ln.split('=',1)[1].strip()
    return '?'
print('auto_unpause 5 -> ' + msg(e.exec('auto_unpause', ['5'])), flush=True)
print('gamespeed 5   -> ' + msg(e.exec('gamespeed', ['5'])), flush=True)
print('等 6 秒让游戏 tick...', flush=True)
time.sleep(6)
print('现在: ' + msg(e.exec('setgamedate', [])), flush=True)
fh.detach(session)
spec2 = iu.spec_from_file_location('fh2', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh2 = iu.module_from_spec(spec2); spec2.loader.exec_module(fh2)
pid, session, sc, fresh = fh2.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/modules/gamedate/game_date_read.js', force_spawn=False)
d = sc.exports_sync
time.sleep(0.5)
print('--- raw ---', flush=True)
print('  ' + d.getDate(), flush=True)
print('--- +0x460..0x4C0 ---', flush=True)
print('  ' + d.peek(0x460, 24), flush=True)
print('  (+0x478=年 +0x47C=本月天数 +0x480=日-1? +0x484=dayOfYear-1? +0x488=月-1)', flush=True)
print('--- 找 15 (小时) 在 0x460..0x600 ---', flush=True)
print('  ' + d.find(15, 0x460, 0x600), flush=True)
fh2.detach(session)
