import sys, importlib.util as iu
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
s = iu.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = iu.module_from_spec(s); s.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/exec_console_command.js', force_spawn=False)
e = sc.exports_sync
import time; time.sleep(0.5)
def show(cmd, args):
    r = e.exec(cmd, args)
    msg = '?'
    for ln in str(r).split(chr(10)):
        if 'out->message' in ln: msg = ln.split('=',1)[1].strip()
    print('  %-28s -> %s' % (cmd + ' ' + ' '.join(args), msg), flush=True)
print('=== 原生指令 (无参数) ===', flush=True)
for c in ['gamespeed', 'auto_unpause', 'event', 'help', 'man']:
    show(c, [])
print('=== 我们的指令 (无参数) ===', flush=True)
for c in ['setgamedate', 'addtimeforyears', 'addtimeformonths', 'addtimefordays', 'addtimeforhours', 'setcamheight', 'setcameraheight_lowerlimit', 'setcameraheight_upperlimit']:
    show(c, [])
print('=== 我们的一条带参数的 (对照) ===', flush=True)
show('setgamedate', ['510.6.7.0'])
fh.detach(session)
