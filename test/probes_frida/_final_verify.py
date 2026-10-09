import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_exec_cmd.js', force_spawn=False)
time.sleep(0.3)
e = sc.exports_sync
t0 = time.time()
ok = False
while time.time() - t0 < 180:
    st = e.ready()
    if st.get('ok'): ok = True; break
    time.sleep(0.5)
print('进地图: %s  用时 %.1f 秒' % (ok, time.time()-t0))
if not ok: sys.exit(1)
print()
print('%-11s %-7s %-6s %-11s' % ('事件','参数','ok','高度'))
for ev, want in [('camtest.1',1500), ('camtest.2',999), ('camtest.1',1500), ('camtest.2',999)]:
    r = str(e.exec('event', [ev]))
    okk = r.split('out->ok')[1].split(chr(10))[0].strip() if 'out->ok' in r else '?'
    time.sleep(1.3)
    h = e.camHeight()
    mark = 'OK' if abs(h-want) < 0.5 else '不匹配'
    print('%-11s %-7d %-6s %-11.2f %s' % (ev, want, okk, h, mark))
print()
print('=== efftip (每次调用的文本) ===')
lg = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/mod_loader_tbb.log'
for l in open(lg, encoding='utf-8', errors='replace').read().splitlines():
    if 'efftip' in l and 'text=[' in l: print('  ' + l)
