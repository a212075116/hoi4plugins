import sys, time, socket
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
t0 = time.time()
while time.time() - t0 < 90:
    s = socket.socket()
    s.settimeout(0.5)
    try:
        s.connect(('127.0.0.1', 19531))
        s.close()
        print('服务已就绪 (%.1f 秒)' % (time.time()-t0))
        break
    except Exception:
        s.close()
        time.sleep(0.5)
else:
    print('服务未就绪 (超时)')
