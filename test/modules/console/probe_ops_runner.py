# -*- coding: utf-8 -*-
import sys, time, subprocess, importlib.util
ROOT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins'
sys.path.insert(0, ROOT + '/test/lib')
spec = importlib.util.spec_from_file_location('fh', ROOT + '/test/lib/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(ROOT + '/test/lib/probe_var_ops.js', force_spawn=False)
print('attached pid=%s' % pid, flush=True)
sc.exports_sync.reset()
time.sleep(0.5)
subprocess.run([sys.executable, '-u', ROOT + '/test/modules/console/numtest_trigger_events.py', 'zzdatetest.86'])
time.sleep(2.5)
print('HITS=' + sc.exports_sync.dump(), flush=True)
fh.detach(session)
print('done', flush=True)
