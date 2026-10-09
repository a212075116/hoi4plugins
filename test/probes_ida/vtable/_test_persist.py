import sys, time
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
import idalib_cli as C
print('ping:', C.send({'op':'ping'}).get('funcs'))
t0 = time.time()
n = 0
for i in range(2000):
    r = C.send({'op':'bytes','ea':'0x140001000','n':8})
    if r.get('ok'): n += 1
el = time.time() - t0
print('2000 次请求成功 %d, 用时 %.1fs (%.2f ms/次)' % (n, el, el*1000/2000))
