# -*- coding: utf-8 -*-
import sys, time, importlib.util
ROOT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins'
sys.path.insert(0, ROOT + '/test/lib')
spec = importlib.util.spec_from_file_location('fh', ROOT + '/test/lib/frida_host.py')
fh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fh)

pid, session, sc, fresh = fh.connect(ROOT + '/test/lib/exec_console_command.js', force_spawn=False)
e = sc.exports_sync
print('attach pid=%s fresh=%s' % (pid, fresh), flush=True)
time.sleep(1.0)

CASES = [
    ('setgamedate', []),
    ('setgamedate', ['1940.1.1']),
    ('setgamedate', ['1940.1.1.12']),
    ('addtimeforyears', []),
    ('addtimeforyears', ['1']),
    ('addtimeformonths', []),
    ('addtimeformonths', ['3']),
    ('addtimefordays', []),
    ('addtimefordays', ['10']),
    ('addtimeforhours', []),
    ('addtimeforhours', ['5']),
    ('setcamheight', []),
    ('setcamheight', ['800']),
    ('setcameraheight_lowerlimit', []),
    ('setcameraheight_lowerlimit', ['150']),
    ('setcameraheight_lowerlimit', ['2500']),
    ('setcameraheight_upperlimit', []),
    ('setcameraheight_upperlimit', ['3000']),
]

def field(txt, key):
    for ln in str(txt).split(chr(10)):
        if key in ln:
            return ln.split('=', 1)[1].strip()
    return '?'

print('', flush=True)
print('命令'.ljust(30) + '参数'.ljust(14) + 'ok'.ljust(5) + 'message', flush=True)
print('-' * 110, flush=True)
for name, args in CASES:
    try:
        r = e.exec(name, args)
    except Exception as ex:
        print(name.ljust(30) + str(args).ljust(14) + 'EXC ' + str(ex)[:60], flush=True)
        continue
    ok = field(r, 'out->ok')
    msg = field(r, 'out->message')
    print(name.ljust(30) + (','.join(args) if args else '(none)').ljust(14) + ok.ljust(5) + msg, flush=True)
    time.sleep(0.6)

print('', flush=True)
print('=== 收尾: 摄像机状态 ===', flush=True)
print(e.cam(), flush=True)
print(e.camLimits(), flush=True)
fh.detach(session)
