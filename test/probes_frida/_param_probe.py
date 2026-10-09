import sys, time, importlib.util, os
os.chdir(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
fh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_exec_cmd.js', force_spawn=False)
time.sleep(0.5)
e = sc.exports_sync
def cam(): return e.cam().replace(chr(10),' ').replace(chr(13),'')
print('初始        : ' + cam())
print()
for ev, want in [('camtest.1','1500'), ('camtest.2','999'), ('camtest.1','1500')]:
    r = str(e.exec('event', [ev]))
    ok = '?'
    if 'out->ok' in r: ok = r.split('out->ok')[1].split(chr(10))[0].strip()
    time.sleep(2.0)
    print('%-11s (期望 %-5s) ok=%-4s -> %s' % (ev, want, ok, cam()))
