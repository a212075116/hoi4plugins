import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_hookfile.js', force_spawn=False)
time.sleep(0.4)
e = sc.exports_sync
print(e.start())
print('等待游戏写崩溃文件前, 先让它跑一会...')
time.sleep(3)
print()
print('=== 现在触发 crashme ===')
# 用另一个 session 执行 crashme 不行, 这里直接调内核: 用 frida 触发
try:
    # 通过 CreateThread 方式已不可用, 直接写一个非法地址到独立线程
    import frida
    s2 = session
    # 用 NativeFunction 调 CreateThread 走游戏自己的路径太绕; 改为直接在这里制造非法写
    sc2 = session.create_script('rpc.exports={go:function(){var t=Process.getCurrentThreadId();Process.setExceptionHandler(function(){});var a=ptr(0);a.writeU8(1);return 1;}}')
    sc2.load()
    try:
        sc2.exports_sync.go()
    except Exception as ex:
        print('(预期) %s' % str(ex)[:100])
except Exception as ex:
    print('触发失败: %s' % str(ex)[:200])
time.sleep(15)
print()
print('=== 捕获到的路径 ===')
print(e.dump())
