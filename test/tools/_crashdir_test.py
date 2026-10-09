import sys, time, importlib.util, os
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)

CD = os.path.join(os.path.expanduser('~'), 'Documents', 'Paradox Interactive', 'Hearts of Iron IV', 'crashes')
def count_docs():
    try: return len([d for d in os.listdir(CD) if os.path.isdir(os.path.join(CD, d))])
    except Exception: return -1
def count_root():
    p = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/crashes'
    try: return len([d for d in os.listdir(p) if os.path.isdir(os.path.join(p, d))])
    except Exception: return -1

print('崩溃前  Documents=%d   Gameroot=%d' % (count_docs(), count_root()))

pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_exec_cmd.js', force_spawn=False)
time.sleep(0.3)
e = sc.exports_sync
t0 = time.time()
while time.time() - t0 < 120:
    if e.ready().get('ok'): break
    time.sleep(0.5)
print('就绪 %.1f 秒' % (time.time()-t0))
print()
print('=== 执行 debug_crash (预期游戏退出) ===')
try:
    r = e.exec('debug_crash', [])
    print(str(r)[:300])
except Exception as ex:
    print('exec 抛异常(预期): %s' % str(ex)[:120])

time.sleep(12)
print()
print('崩溃后  Documents=%d   Gameroot=%d' % (count_docs(), count_root()))
p = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/crashes'
if os.path.isdir(p):
    subs = sorted(os.listdir(p))
    print('游戏根目录 crashes 内容: ' + str(subs[-3:]))
