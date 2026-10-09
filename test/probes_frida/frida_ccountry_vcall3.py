# frida_ccountry_vcall3.py -- 统计 CCountry 各虚函数的调用次数
#
# 用 Interceptor.attach 直接挂在虚表里的函数地址上。
# 计数是全局的(不分实例), 但目的就是"这些函数到底有没有被调用、哪个最热",
# 全局计数已经足够, 不需要逐实例打桩。
#
# 判据: 挂上之后等一段时间, 有非零计数就说明该槽真的在被调用。
import frida, time, json

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
JS = '''
var base = Process.enumerateModules()[0].base;
var VT = base.add(0x27E7360);
var NSLOT = 11;
var counts = {};
var addrs = [];
rpc.exports.install = function () {
    for (var s = 0; s < NSLOT; s++) {
        var fn = VT.add(s * 8).readPointer();
        addrs.push(fn.toString());
        counts[s] = 0;
        (function (slot) {
            try {
                Interceptor.attach(fn, { onEnter: function () { counts[slot]++; } });
            } catch (e) { counts[slot] = -1; }
        })(s);
    }
    return {addrs: addrs};
};
rpc.exports.counts = function () { return counts; };
'''

def wait_for_map(timeout=300):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            if 'Launching SINGLEPLAYER-game' in open(GAMELOG, encoding='utf-8', errors='ignore').read():
                return True
        except Exception: pass
        time.sleep(0.4)
    return False

pid = frida.spawn([EXE, '-continuelastsave', '-hands_off', '-gdpr-compliant'])
session = frida.attach(pid)
sc = session.create_script(JS)
sc.load()
print('[spawn] pid=%d' % pid, flush=True)
frida.resume(pid)
print('[map] = %s' % wait_for_map(), flush=True)
time.sleep(3)
r = sc.exports_sync.install()
print('[已挂载] CCountry 虚表 %d 个槽' % len(r['addrs']))
for i, a in enumerate(r['addrs']):
    off = int(a, 16) - int(hex(0), 16)
    print('    slot %2d -> %s' % (i, a))
print('[观察] 20 秒...', flush=True)
time.sleep(25)
c = sc.exports_sync.counts()
print('[调用计数]')
for k in sorted(c.keys(), key=lambda x: int(x)):
    print('    slot %2s : %s' % (k, c[k]))
try: frida.kill(pid)
except Exception: pass