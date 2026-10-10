import sys, time
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
import hoi4_launch as HL
dt, info = HL.build_and_launch(marker='[plugin] Camera_RegisterCommands', skip_build=True)
print('部署: ' + str(info))
print('就绪 %.2f 秒' % dt)
import importlib.util
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/exec_console_command.js', force_spawn=False)
time.sleep(0.3)
e = sc.exports_sync
t0 = time.time()
while time.time() - t0 < 90:
    if e.ready()['ok']: break
    time.sleep(0.4)
print('摄像机就绪')
print(e.exec('event', ['camtest.1'])[:120])
time.sleep(2.0)
print('高度 = %.2f' % e.camHeight())
print()
print('=== efftip ===')
for line in HL.read_log().splitlines():
    if 'efftip' in line: print('  ' + line)
