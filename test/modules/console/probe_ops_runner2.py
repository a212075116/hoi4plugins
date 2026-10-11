# -*- coding: utf-8 -*-
import sys, time, importlib.util
ROOT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins'
sys.path.insert(0, ROOT + '/test/lib')
spec = importlib.util.spec_from_file_location('fh', ROOT + '/test/lib/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(ROOT + '/test/lib/probe_exec_console.js', force_spawn=False)
e = sc.exports_sync
print('attached pid=%s' % pid, flush=True)
print('reset=' + e.resetHits(), flush=True)
r = e.exec('event', ['zzdatetest.86'])
print('trigger -> ' + r.replace(chr(10), ' | ')[:200], flush=True)
time.sleep(2.5)
print('HITS=' + e.dumpHits(), flush=True)
fh.detach(session)
print('done', flush=True)
