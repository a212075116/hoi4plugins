import sys, importlib.util as iu, time, re
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
s = iu.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = iu.module_from_spec(s); s.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/exec_console_command.js', force_spawn=False)
e = sc.exports_sync
time.sleep(0.5)
def st():
    c = e.cam()
    g = {}
    for m in re.finditer(r'\+0x([0-9A-Fa-f]+)\([^)]*\)=([-+0-9.eE]+)', c):
        g[int(m.group(1),16)] = float(m.group(2))
    return g
def show(label):
    g = st()
    print('  %-26s 实际+678=%-9.2f 目标+69C=%-9.2f' % (label, g.get(0x678,0), g.get(0x69C,0)), flush=True)
print('=== 用户操作复现: 下限改高到超过当前高度 ===', flush=True)
show('起始')
print('', flush=True)
print('--- 执行 setcameraheight_lowerlimit 2000 (当前高度远低于 2000) ---', flush=True)
r = e.exec('setcameraheight_lowerlimit', ['2000'])
print('  指令返回: ' + r.split('message=')[1].split(chr(10))[0].strip() if 'message=' in r else '  ?', flush=True)
for t in (0.3, 0.8, 1.5, 2.5, 4.0):
    time.sleep(t if t == 0.3 else 0.7 if t == 0.8 else 0.7 if t == 1.5 else 1.0 if t == 2.5 else 1.5)
    show('指令后约 %.1fs' % t)
print('', flush=True)
print('--- 再执行 setcameraheight_lowerlimit 300 ---', flush=True)
e.exec('setcameraheight_lowerlimit', ['300'])
time.sleep(1.0); show('恢复下限 300 后 1s')
time.sleep(2.0); show('恢复下限 300 后 3s')
fh.detach(session)
