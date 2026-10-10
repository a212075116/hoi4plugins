import sys, importlib.util as iu, time, math, re
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
s = iu.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = iu.module_from_spec(s); s.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/exec_console_command.js', force_spawn=False)
e = sc.exports_sync
time.sleep(0.5)
def rd():
    c = e.camLimits()
    d = {}
    for m in re.finditer(r'\+0x([0-9A-Fa-f]+)\s+u32=(\d+)\s+i32=(-?\d+)\s+f32=([-+0-9.eE]+)', c):
        d[int(m.group(1),16)] = (int(m.group(3)), float(m.group(4)))
    return d
def show(label):
    d = rd()
    lo = d.get(0x6D0, (None,))[0]
    hi = d.get(0x6D4, (None,))[0]
    h  = d.get(0x69C, (None, 0))[1]
    h678 = d.get(0x678, (None, 0))[1]
    nan = math.isnan(h) or math.isnan(h678)
    print('  %-34s lo=%-6s hi=%-6s 目标=%-10.2f 当前=%-10.2f %s' % (
        label, lo, hi, h, h678, '★★★ NaN' if nan else 'OK'), flush=True)
    return nan
print('=== 测边界值 35 / 50 (游戏原生下限=50) ===', flush=True)
show('当前基线')
print('', flush=True)
print('第1步: 先设 lower=35 (低于原生下限50)', flush=True)
e.exec('setcameraheight_lowerlimit', ['35']); time.sleep(1.3)
if show('lower=35'): raise SystemExit('已 NaN, 停止')
print('', flush=True)
print('第2步: 设 upper=35 (与lo相等, 且低于原生下限)', flush=True)
e.exec('setcameraheight_upperlimit', ['35']); time.sleep(1.3)
if show('upper=35'): raise SystemExit('已 NaN, 停止')
print('', flush=True)
print('第3步: 设 upper=51 (略高于原生下限)', flush=True)
e.exec('setcameraheight_upperlimit', ['51']); time.sleep(1.3)
if show('upper=51'): raise SystemExit('已 NaN, 停止')
print('', flush=True)
print('第4步: 设 lower=50 upper=60', flush=True)
e.exec('setcameraheight_lowerlimit', ['50']); time.sleep(1.0)
e.exec('setcameraheight_upperlimit', ['60']); time.sleep(1.3)
show('lo=50 hi=60')
fh.detach(session)
