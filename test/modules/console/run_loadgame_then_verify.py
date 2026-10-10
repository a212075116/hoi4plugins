# -*- coding: utf-8 -*-
import sys, time, importlib.util
ROOT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins'
sys.path.insert(0, ROOT + '/test/lib')
spec = importlib.util.spec_from_file_location('fh', ROOT + '/test/lib/frida_host.py')
fh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(ROOT + '/test/lib/exec_console_command.js', force_spawn=False)
e = sc.exports_sync
print('attach pid=%s' % pid, flush=True)

print('baseline event 63:', e.exec('event', ['zzdatetest.63'])[:160].replace(chr(10), ' | '), flush=True)
time.sleep(3.0)

savefile = sys.argv[1] if len(sys.argv) > 1 else 'zz_reload_test'
print('loadgame ' + savefile + ':', e.exec('loadgame', [savefile])[:220].replace(chr(10), ' | '), flush=True)
time.sleep(10.0)

print('after event 63:', e.exec('event', ['zzdatetest.63'])[:160].replace(chr(10), ' | '), flush=True)
time.sleep(3.0)
fh.detach(session)
print('done', flush=True)
