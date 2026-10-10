import sys, time, importlib.util as iu
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
s = iu.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
fh = iu.module_from_spec(s); s.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_exec_cmd.js', force_spawn=False)
e = sc.exports_sync
time.sleep(0.5)
def msg(r):
    for ln in str(r).split(chr(10)):
        if 'out->message' in ln: return ln.split('=',1)[1].strip()
    return '?'
print('auto_unpause 2 -> ' + msg(e.exec('auto_unpause', ['2'])), flush=True)
for i in range(5):
    time.sleep(4)
    print('  T+%2ds  日期: %s' % ((i+1)*4, msg(e.exec('setgamedate', []))), flush=True)
print('--- 若日期不变说明仍在暂停 ---', flush=True)
fh.detach(session)
