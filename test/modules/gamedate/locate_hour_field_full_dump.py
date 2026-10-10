import sys, time, importlib.util as iu
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
spec = iu.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = iu.module_from_spec(spec); spec.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/modules/gamedate/game_date_read.js', force_spawn=False)
d = sc.exports_sync
time.sleep(0.5)
print('raw: ' + d.getDate(), flush=True)
raw = d.peek(0x468, 1)
import re
m = re.search(r'=(-?\d+)', str(raw))
rv = int(m.group(1))
h = ((rv - 43800000) % 24)
print('推算小时 = %d' % h, flush=True)
print('--- +0x460..0x540 ---', flush=True)
print('  ' + d.peek(0x460, 40), flush=True)
print('--- 找小时值 %d 在 0x460..0x700 ---' % h, flush=True)
print('  ' + d.find(h, 0x460, 0x700), flush=True)
fh.detach(session)
