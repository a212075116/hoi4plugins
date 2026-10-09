import sys, time
sys.path.insert(0, 'flirt/loader')
import frida_host as fh
pid, session, sc, fresh = fh.connect('flirt/loader/_cmd_check.js', force_spawn=False)
time.sleep(0.5)
print('=== 命令表尾部 ===')
print(sc.exports_sync.dump())
print()
print('=== 搜索 sethcam ===')
print(sc.exports_sync.find('sethcam'))
