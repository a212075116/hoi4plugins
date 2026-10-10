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
print('auto_unpause: ' + msg(e.exec('auto_unpause', ['2'])), flush=True)
print('等 25 秒让游戏稳定...', flush=True)
time.sleep(25)
print('稳定后日期: ' + msg(e.exec('setgamedate', [])), flush=True)
print(flush=True)
print('=== 基准 510.6.7.0 ===', flush=True)
print('  ' + msg(e.exec('setgamedate', ['510.6.7.0'])), flush=True)
time.sleep(3)
print('  现在: ' + msg(e.exec('setgamedate', [])), flush=True)
tests = [
    ('addtimeforyears', '10',  '加 10 年 -> 期望 520.6.7'),
    ('addtimeformonths', '3',  '加 3 月 -> 期望 520.9.7'),
    ('addtimefordays', '45',   '加 45 天'),
    ('addtimeforhours', '100', '加 100 小时'),
    ('addtimefordays', '-30',  '减 30 天'),
    ('addtimeformonths', '-5', '减 5 月'),
    ('addtimeforyears', '-3',  '减 3 年'),
    ('addtimeforhours', '-50', '减 50 小时'),
]
for cmd, a, note in tests:
    print('=== %s %s  (%s) ===' % (cmd, a, note), flush=True)
    print('  ' + msg(e.exec(cmd, [a])), flush=True)
    time.sleep(3)
    print('  现在: ' + msg(e.exec('setgamedate', [])), flush=True)
fh.detach(session)
