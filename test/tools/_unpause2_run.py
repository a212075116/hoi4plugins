import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_exec_cmd.js', force_spawn=False)
print('fresh=%s' % fresh, flush=True)
e = sc.exports_sync
time.sleep(0.5)
def gs():
    b = __import__('frida').get_local_device() if False else None
    return None
print('=== auto_unpause 3 ===', flush=True)
r = e.exec('auto_unpause', ['3'])
for ln in str(r).split(chr(10)):
    if 'message' in ln: print('  ' + ln.strip(), flush=True)
time.sleep(0.5)
print('=== gamespeed 3 ===', flush=True)
r = e.exec('gamespeed', ['3'])
for ln in str(r).split(chr(10)):
    if 'message' in ln: print('  ' + ln.strip(), flush=True)
time.sleep(5)
print('=== 再回显日期 ===', flush=True)
r = e.exec('setgamedate', [])
for ln in str(r).split(chr(10)):
    if 'message' in ln: print('  ' + ln.strip(), flush=True)
fh.detach(session)
