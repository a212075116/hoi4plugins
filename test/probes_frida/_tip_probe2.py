import sys, time, traceback
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
import hoi4_launch as HL
import importlib.util
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_exec_cmd.js', force_spawn=False)
time.sleep(0.3)
e = sc.exports_sync
print('ready: ' + str(e.ready()))
print('camHeight: ' + str(e.camHeight()))
print()
print('=== 调 event camtest.1, 打印完整结果 ===')
try:
    r = e.exec('event', ['camtest.1'])
    print(repr(r))
except Exception:
    traceback.print_exc()
print()
time.sleep(2.0)
print('camHeight: ' + str(e.camHeight()))
print()
print('=== 对照: 调一个已知能用的命令 ===')
try:
    print(repr(e.exec('help', ['event']))[:400])
except Exception:
    traceback.print_exc()
