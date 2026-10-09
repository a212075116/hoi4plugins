import sys, time
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
import hoi4_launch as HL, probe_common as PC
dt, info = HL.build_and_launch(marker='[plugin] Camera_RegisterCommands')
print('部署 %s  就绪 %.2f 秒' % (info, dt))
e = PC.connect_and_wait(timeout=180)
print('摄像机 %.2f' % e.camHeight())
print(e.exec('event', ['camtest.1'])[:120])
time.sleep(1.5)
print('摄像机之后 %.2f' % e.camHeight())
print()
print('=== efftip ===')
for l in HL.read_log().splitlines():
    if 'efftip' in l: print('  ' + l)
print('=== error.log camtest ===')
import os
lg = os.path.join(os.path.expanduser('~'), 'Documents', 'Paradox Interactive', 'Hearts of Iron IV', 'logs', 'error.log')
try:
    for l in open(lg, encoding='utf-8', errors='replace').read().splitlines()[-400:]:
        if 'camtest' in l or 'EFFECT_SET' in l: print('  ' + l)
except Exception as ex: print('  ' + str(ex))
