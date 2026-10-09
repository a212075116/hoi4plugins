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
print('=== 基准 setgamedate 510.6.7.0 ===', flush=True)
print('  ' + msg(e.exec('setgamedate', ['510.6.7.0'])), flush=True)
time.sleep(3)
print('  现在: ' + msg(e.exec('setgamedate', [])), flush=True)
evs = [
    ('zzdatetest.4',  'effect add_time_for_years = 10'),
    ('zzdatetest.5',  'effect add_time_for_months = 3'),
    ('zzdatetest.6',  'effect add_time_for_days = 45'),
    ('zzdatetest.7',  'effect add_time_for_hours = 100'),
    ('zzdatetest.8',  'effect add_time_for_days = -30'),
    ('zzdatetest.9',  'effect add_time_for_months = -5'),
    ('zzdatetest.10', 'effect add_time_for_years = -3'),
    ('zzdatetest.11', 'effect add_time_for_hours = -50'),
]
for ev, note in evs:
    print('=== %s  (%s) ===' % (ev, note), flush=True)
    e.exec('event', [ev])
    time.sleep(3)
    print('  现在: ' + msg(e.exec('setgamedate', [])), flush=True)
fh.detach(session)
