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
time.sleep(1.0)
cmd = sys.argv[1]
args = sys.argv[2:]
out = e.exec(cmd, args)
print('exec %s %s -> %s' % (cmd, args, out[:300].replace(chr(10), ' | ')), flush=True)
time.sleep(float(3.0))
fh.detach(session)
print('done', flush=True)
