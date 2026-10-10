import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/modules/gamedate/game_date_read.js', force_spawn=False)
e = sc.exports_sync
time.sleep(0.5)
print('raw  : ' + str(e.getDate()), flush=True)
print('字段 : ' + str(e.peek(0x460, 14)), flush=True)
print('       (+0x478 年  +0x47C 本月天数  +0x480 日-1  +0x484 dayOfYear-1  +0x488 月-1)', flush=True)
fh.detach(session)
