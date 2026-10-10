import sys, importlib.util as iu, time, re
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
s = iu.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = iu.module_from_spec(s); s.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/exec_console_command.js', force_spawn=False)
e = sc.exports_sync
time.sleep(0.5)
def h678():
    return float(e.cam().split('+0x678(当前)=')[1].split()[0])
def pause():
    return e.exec('pause', [])
print('=== 测: 暂停 vs 运行 时 setcamheight 是否生效 ===', flush=True)
print('  初始高度: %.2f' % h678(), flush=True)
print('', flush=True)
print('--- A) 先暂停 ---', flush=True)
print('  ' + pause().split('message=')[1].strip(), flush=True)
time.sleep(1)
e.exec('setcamheight', ['900'])
for i in (0.3, 1.0, 2.0, 3.0):
    time.sleep(i if i == 0.3 else (i - prev if False else 0.7))
    print('   暂停中 +%.1fs: +678=%.2f' % (i, h678()), flush=True)
    prev = i
print('', flush=True)
print('--- B) 恢复运行 ---', flush=True)
pause()
time.sleep(2.5)
print('   运行 2.5s 后: +678=%.2f' % h678(), flush=True)
print('', flush=True)
print('--- C) 运行中再设一次 ---', flush=True)
e.exec('setcamheight', ['1400'])
time.sleep(2.5)
print('   运行 2.5s 后: +678=%.2f' % h678(), flush=True)
fh.detach(session)
