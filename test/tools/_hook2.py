import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_exec_cmd.js', force_spawn=False)
time.sleep(0.4)
e = sc.exports_sync
print(e.hookFiles())
t0 = time.time()
while time.time() - t0 < 120:
    if e.ready().get('ok'): break
    time.sleep(0.5)
print('就绪 %.1f 秒' % (time.time()-t0))
print()
print('=== 触发 crashme ===')
try:
    print(str(e.exec('crashme', []))[:200])
except Exception as ex:
    print('(预期) %s' % str(ex)[:120])
time.sleep(20)
print()
print('=== 捕获到的文件路径 ===')
try:
    print(e.fileLog())
except Exception as ex:
    print('(脚本已随进程销毁) %s' % str(ex)[:100])
