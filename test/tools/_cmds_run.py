import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
fh.set_start_tag('ABY')
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_exec_cmd.js', force_spawn=True, wait=False)
e = sc.exports_sync
time.sleep(0.5)
r = fh.wait_game_ready(session, timeout=120)
if r is None: print('超时'); sys.exit(1)
print('--- 搜全部命令里含 date/calendar/clock/hour 的 ---', flush=True)
allc = e.listCmds('')
for line in allc.split(chr(10)):
    low = line.lower()
    if any(k in low for k in ['date','calendar','clock','hour','advance','skip']):
        print('  ' + line, flush=True)
print('--- 连续读 time 6 次 (每次隔 2 秒), 看是否推进 ---', flush=True)
for i in range(6):
    r2 = e.exec('time', [])
    msg = ''
    for ln in str(r2).split(chr(10)):
        if 'out->message' in ln: msg = ln.strip()
    print('  #%d %s' % (i, msg), flush=True)
    time.sleep(2)
fh.detach(session)
