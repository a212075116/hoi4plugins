import sys, importlib.util as iu, time, re
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
s = iu.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = iu.module_from_spec(s); s.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/modules/camera/camera_setter_probe.js', force_spawn=False)
d = sc.exports_sync
time.sleep(0.5)
def g(off):
    t = d.dump()
    for line in t.split(chr(10)):
        m = re.match(r'\+0x([0-9a-f]+)\s+([-0-9.]+)', line)
        if m and int(m.group(1),16) == off: return m.group(2)
    return '?'
print('=== 当前状态 ===', flush=True)
print('  实际高度 +678 = ' + str(g(0x678)), flush=True)
print('  目标高度 +69C = ' + str(g(0x69C)), flush=True)
print('  +6B0 flag    = ' + str(g(0x6b0)), flush=True)
print('', flush=True)
print('=== 手动调 setter 看是否插值 ===', flush=True)
d.oldSet(2000)
for wait in (0.3, 1.0, 2.0):
    time.sleep(wait if wait==0.3 else (0.7 if wait==1.0 else 1.0))
    print('  +%.1fs: +678=%s  +69C=%s  +6B0=%s' % (wait, g(0x678), g(0x69C), g(0x6b0)), flush=True)
fh.detach(session)
