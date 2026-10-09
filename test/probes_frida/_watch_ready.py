import sys, time
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
import hoi4_launch as HL
dt, _ = HL.launch(wait_marker='[plugin] Camera_RegisterCommands', timeout=120)
print('插件就绪 %.2f 秒' % dt)
e = None
try:
    import probe_common as PC
    e = PC.connect()
except Exception as ex:
    print('frida 连接失败: ' + str(ex)); sys.exit(1)
t0 = time.time()
last = None
for i in range(90):
    st = e.ready()
    s = str(st)
    if s != last:
        print('%6.1fs  %s' % (time.time() - t0, s))
        last = s
    if st.get('ok'):
        print('=> 进地图了, 用时 %.1f 秒' % (time.time() - t0))
        break
    time.sleep(1.0)
else:
    print('=> 90 秒内没进地图, 最后状态: ' + str(last))
