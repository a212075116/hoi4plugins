"""Start hoi4 and report progress every second until the camera is usable."""
import sys, time
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
import hoi4_launch as HL

t0 = time.time()
print('%-8s %s' % ('t', 'state'))

# phase 1: start (kill + deploy already done), wait plugin marker
HL.kill(); HL.clear_log()
import subprocess, os
subprocess.Popen([HL.EXE, '-gdpr-compliant', '-start_tag=CHI', '-nolauncher'], cwd=HL.ROOT)
print('%6.1fs  已启动' % (time.time() - t0))

e = None
last = None
logmark = None
for i in range(240):
    t = time.time() - t0
    if not HL.proc_alive():
        print('%6.1fs  进程已退出' % t)
        break
    txt = HL.read_log()
    if logmark is None and '[plugin] Camera_RegisterCommands' in txt:
        logmark = t
        print('%6.1fs  插件完全就绪' % t)
    if logmark is not None and e is None:
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location('pc', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/probe_common.py')
            pc = importlib.util.module_from_spec(spec); spec.loader.exec_module(pc)
            e = pc.connect()
            print('%6.1fs  frida 已连接' % t)
        except Exception as ex:
            print('%6.1fs  frida 连接失败: %s' % (t, ex))
    if e is not None:
        try:
            st = e.ready()
            s = str(st)
            if s != last:
                print('%6.1fs  ready=%s' % (t, s))
                last = s
            if st.get('ok'):
                print('%6.1fs  => 进地图完成, 总耗时 %.1f 秒' % (t, t))
                break
        except Exception as ex:
            print('%6.1fs  ready 调用失败: %s' % (t, ex)); break
    time.sleep(1.0)
else:
    print('=> 240 秒仍未进地图')
