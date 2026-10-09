import sys, time, importlib.util, os
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_boom.js', force_spawn=False)
time.sleep(0.4)
print('已 attach pid=%s, 制造崩溃...' % pid)
try:
    sc.exports_sync.boom()
except Exception as ex:
    print('(预期异常) %s' % str(ex)[:150])
for i in range(20):
    time.sleep(1)
    if not fh.proc_alive() if hasattr(fh,'proc_alive') else False:
        break
print('等待崩溃报告写入...')
