import sys, os, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
import hoi4_launch as HL

def attach():
    spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
    fh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fh)
    pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_exec_cmd.js', force_spawn=False)
    time.sleep(0.3)
    return sc.exports_sync

dt, _ = HL.launch(wait_marker='[plugin] Camera_RegisterCommands', timeout=150)
print('插件就绪 %.2f 秒' % dt)

e = attach()
t0 = time.time()
while time.time() - t0 < 120:
    st = e.ready()
    if st['ok']:
        print('摄像机可测 (轮询 %.2f 秒): %s' % (time.time() - t0, st))
        break
    time.sleep(0.4)
else:
    print('超时: ' + str(e.ready()))
    sys.exit(1)

print()
print('%-11s %-7s %-6s %s' % ('事件', '参数', 'ok', '摄像机 +0x69C'))
allok = True
for ev, want in [('camtest.1', 1500), ('camtest.2', 999), ('camtest.1', 1500), ('camtest.2', 999)]:
    r = str(e.exec('event', [ev]))
    ok = r.split('out->ok')[1].split(chr(10))[0].strip() if 'out->ok' in r else '?'
    time.sleep(1.5)
    got = e.camHeight()
    mark = 'OK' if abs(got - want) < 0.5 else '不匹配'
    if mark != 'OK': allok = False
    print('%-11s %-7d %-6s %-10.2f %s' % (ev, want, ok, got, mark))
print()
print('全部通过' if allok else '有失败')
print()
print('=== 执行日志 ===')
for line in HL.read_log().splitlines():
    if '[eff] exec' in line: print('  ' + line)
