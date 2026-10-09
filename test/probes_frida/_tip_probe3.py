import sys, time, traceback
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
import hoi4_launch as HL
import probe_common as PC

e = PC.connect_and_wait(timeout=150)
print('camHeight 起始 = %.2f' % e.camHeight())
print()
print('=== event camtest.1 ===')
try:
    print(e.exec('event', ['camtest.1'])[:300])
except Exception:
    traceback.print_exc()
time.sleep(2.5)
print('camHeight 之后 = %.2f' % e.camHeight())
print()
print('=== 事件文本 (efftip) ===')
lines = [l for l in HL.read_log().splitlines() if 'efftip' in l or '[eff] exec' in l]
for l in lines: print('  ' + l)
if not lines: print('  (无)')
