# -*- coding: utf-8 -*-
import sys, time, importlib.util
ROOT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins'
sys.path.insert(0, ROOT + '/test/lib')
spec = importlib.util.spec_from_file_location('fh', ROOT + '/test/lib/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(ROOT + '/test/lib/exec_console_command.js', force_spawn=False)
e = sc.exports_sync
tests = [
  ('A int64',  'set_variable64 = { var = ta value = 92233720368546 }'),
  ('B dec64',  'set_variable64 = { var = tb value = 92233720368546.05 }'),
  ('C vanilla dec', 'set_variable = { tc = 1.5 }'),
  ('D vanilla big', 'set_variable = { td = 92233720368546 }'),
  ('E vanilla small', 'set_variable = { te = 8000 }'),
]
for label, cmd in tests:
    r = e.exec('eval_effect', [cmd])
    print(label + ' => ' + r.replace(chr(10), ' | ')[:300], flush=True)
    time.sleep(1.5)
r = e.exec('event', ['zzdatetest.65'])
print('ev65 => ' + r.replace(chr(10), ' | ')[:200], flush=True)
time.sleep(2.0)
fh.detach(session)
print('done', flush=True)
