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
print('auto_unpause: ' + msg(e.exec('auto_unpause', ['3'])), flush=True)
print('gamespeed:    ' + msg(e.exec('gamespeed', ['3'])), flush=True)
print('现在日期(命令): ' + msg(e.exec('setgamedate', [])), flush=True)
print('=== event zzdatetest.1 (510.6.7.0) ===', flush=True)
print('  ' + msg(e.exec('event', ['zzdatetest.1'])), flush=True)
fh.detach(session)
print('done', flush=True)
