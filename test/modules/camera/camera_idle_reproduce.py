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
def show(l):
    g = st()
    print('  %-24s +678=%-10.2f +69C=%-10.2f' % (l, g.get(0x678,0), g.get(0x69C,0)), flush=True)
show('起始')
print('', flush=True)
print('--- 闲置 30 秒 (模拟玩家长时间不操作) ---', flush=True)
time.sleep(30)
show('闲置后')
print('', flush=True)
print('--- 闲置后执行: setcameraheight_lowerlimit 2500 (当前高度应该远低于 2500) ---', flush=True)
r = e.exec('setcameraheight_lowerlimit', ['2500'])
print('  返回: ' + (r.split('message=')[1].split(chr(10))[0].strip() if 'message=' in r else '?'), flush=True)
for i in range(1, 9):
    time.sleep(1.0)
    show('+%ds' % i)
fh.detach(session)
