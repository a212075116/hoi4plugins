import sys, time, importlib.util, os
os.chdir(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_dump_entry.js', force_spawn=False)
time.sleep(0.5)
e = sc.exports_sync
for nm in ('setcamheight','setcamraw','setcamnc','debug_zoom','allowdiplo'):
    print(e.argCountGuess(nm))
    print()
