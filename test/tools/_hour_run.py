import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_exec_cmd.js', force_spawn=False)
e = sc.exports_sync
time.sleep(0.5)
def msg(r):
    for ln in str(r).split(chr(10)):
        if 'out->message' in ln: return ln.split('=',1)[1].strip()
    return '?'
print('自动暂停(设为暂停, 便于观察): ' + msg(e.exec('auto_unpause', ['1'])), flush=True)
print('当前: ' + msg(e.exec('setgamedate', [])), flush=True)
fh.detach(session)
import importlib.util as iu
spec2 = iu.spec_from_file_location('fh2', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
fh2 = iu.module_from_spec(spec2); spec2.loader.exec_module(fh2)
pid, session, sc, fresh = fh2.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_date.js', force_spawn=False)
d = sc.exports_sync
time.sleep(0.5)
print('--- 设 510.6.7.15 (小时=15) ---', flush=True)
DAY = 365*10 + 157
raw = 43800000 + (182500 + DAY)*24 + 15
print('  ' + d.setRaw(raw), flush=True)
time.sleep(3)
print('--- dump +0x460..0x4C0 ---', flush=True)
print('  ' + d.peek(0x460, 24), flush=True)
print('--- 找 15 (小时候选) ---', flush=True)
print('  ' + d.find(15, 0x400, 0x600), flush=True)
print('--- 找 157 (dayOfYear-1) ---', flush=True)
print('  ' + d.find(157, 0x400, 0x600), flush=True)
fh2.detach(session)
