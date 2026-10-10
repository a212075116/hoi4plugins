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
def snap(lbl):
    print('  %-20s +678=%-10s +69C=%-10s +6B0=%-6s +680=%-10s +68C=%-10s' % (
        lbl, g(0x678), g(0x69C), g(0x6b0), g(0x680), g(0x68c)), flush=True)
print('=== 用不同的值调用 setter (2100 != 2000) ===', flush=True)
snap('调用前')
d.oldSet(2100)
for i, w in enumerate([0.3, 0.7, 1.0, 2.0]):
    time.sleep(w)
    snap('+%.1fs' % (0.3 + i*0.7 + (w-0.7 if i>0 else 0)))
print('', flush=True)
print('=== 再用同级值 2400 ===', flush=True)
d.oldSet(2400)
time.sleep(0.5); snap('+0.5s')
time.sleep(2.0); snap('+2.5s')
fh.detach(session)
