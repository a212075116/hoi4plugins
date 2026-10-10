import sys, importlib.util as iu, time, re
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
s = iu.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = iu.module_from_spec(s); s.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/exec_console_command.js', force_spawn=False)
e = sc.exports_sync
time.sleep(0.5)
def g(off):
    t = e.camLimits()
    for line in t.split(chr(10)):
        m = re.search(r'\+0x([0-9a-f]+).*f32=([-0-9.]+)', line)
        if m and int(m.group(1),16) == off: return m.group(2)
    return '?'
def snap(lbl):
    print('  %-24s +678=%-10s +69C=%-10s' % (lbl, g(0x678), g(0x69C)), flush=True)
print('=== 用指令 setcamheight 测 (区分指令路径) ===', flush=True)
snap('起始')
print('  -> setcamheight 800', flush=True)
e.exec('setcamheight', ['800'])
time.sleep(0.4); snap('+0.4s')
time.sleep(1.0); snap('+1.4s')
time.sleep(1.5); snap('+2.9s')
print('', flush=True)
print('=== 用指令 setcameraheight_lowerlimit 拉高 ===', flush=True)
print('  -> setcameraheight_lowerlimit 2500', flush=True)
r = e.exec('setcameraheight_lowerlimit', ['2500'])
time.sleep(0.4); snap('+0.4s')
time.sleep(1.0); snap('+1.4s')
time.sleep(1.5); snap('+2.9s')
print('', flush=True)
print('=== 立刻用 frida 直接调同一个 setter 设 2700 ===', flush=True)
fh.detach(session)
time.sleep(0.8)
pid2, s2, sc2, f2 = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/modules/camera/camera_setter_probe.js', force_spawn=False)
d2 = sc2.exports_sync
def d(off):
    t = d2.dump()
    for line in t.split(chr(10)):
        m = re.match(r'\+0x([0-9a-f]+)\s+([-0-9.]+)', line)
        if m and int(m.group(1),16) == off: return m.group(2)
    return '?'
print('  调用前  +678=%s  +69C=%s' % (d(0x678), d(0x69C)), flush=True)
d2.oldSet(2700)
time.sleep(0.4); print('  +0.4s  +678=%s  +69C=%s' % (d(0x678), d(0x69C)), flush=True)
time.sleep(1.5); print('  +1.9s  +678=%s  +69C=%s' % (d(0x678), d(0x69C)), flush=True)
fh.detach(s2)
