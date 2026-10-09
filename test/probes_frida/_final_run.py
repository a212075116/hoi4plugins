import sys, time, importlib.util, os
os.chdir(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
fh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_exec_cmd.js', force_spawn=False)
time.sleep(0.5)
e = sc.exports_sync
def cam(): return e.cam()
print('起始: ' + cam())
print()
for label, args in [
    ('1) 无参数', []),
    ('2) 1200 (范围内)', ['1200']),
    ('3) 9999 (超上限 3000)', ['9999']),
    ('4) -500 (超下限 50)', ['-500']),
    ('5) abc (非法)', ['abc']),
    ('6) 310 (复位)', ['310']),
]:
    print('=== ' + label + ' ===')
    print('  前: ' + cam())
    print(e.exec('setcamheight', args))
    print('  立即: ' + cam())
    time.sleep(1.8)
    print('  1.8s 后: ' + cam())
    print()
