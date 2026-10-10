import sys, importlib.util as iu, time, re
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
s = iu.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = iu.module_from_spec(s); s.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/modules/camera/camera_setter_probe.js', force_spawn=False)
d = sc.exports_sync
time.sleep(0.5)
def key():
    t = d.dump()
    g = {}
    for line in t.split(chr(10)):
        m = re.match(r'\+0x([0-9a-f]+)\s+([-0-9.]+)', line)
        if m: g[int(m.group(1),16)] = m.group(2)
    return g
def show(label):
    g = key()
    print('  %-22s 实际高度+678=%-10s D.y+69C=%-10s E.y+6A8=%-8s' % (
        label, g.get(0x678), g.get(0x69c), g.get(0x6a8)), flush=True)
print('=== 对比两个 setter ===', flush=True)
show('基线')
print('', flush=True)
print('--- 旧: sub_1412643F0 (RVA_CAM_SETH, 我们一直在用) ---', flush=True)
d.oldSet(800); time.sleep(0.2); show('调用后 0.2s')
time.sleep(1.5); show('调用后 1.7s')
print('', flush=True)
print('--- 新: sub_141262730 (同时写 D组与E组) ---', flush=True)
d.callSet(1200); time.sleep(0.2); show('调用后 0.2s')
time.sleep(1.5); show('调用后 1.7s')
print('', flush=True)
print('--- 再等 3 秒看是否被游戏覆盖 ---', flush=True)
time.sleep(3); show('3 秒后')
fh.detach(session)
