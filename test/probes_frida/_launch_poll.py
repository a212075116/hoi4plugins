import sys, os, time
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
import hoi4_launch as HL
print('=== 启动, 轮询等 effect 就绪 ===')
dt1, txt = HL.launch(wait_marker='[eff] camera height effect ready', timeout=120)
print('  effect 就绪耗时: %.2f 秒' % dt1)
print()
print('=== 继续轮询等进地图 (Camera_RegisterCommands 是插件完成了 CGameState 等待) ===')
dt2, txt = HL.wait_for('[plugin] Camera_RegisterCommands', timeout=120)
print('  进地图耗时: %.2f 秒 (总计 %.2f)' % (dt2, dt1 + dt2))
print()
print(HL.status())
