# frida_hunt_country.py -- 全内存搜索 CCountry 的虚表指针, 反推它被谁持有
#
# 前面在 CGameState 里怎么找都找不到国家对象, 说明"猜偏移"这条路本身就不对。
# 反过来做: 先把 CCountry 实例找出来(它的首 8 字节就是虚表指针, 这是个确凿指纹),
# 再看这些实例地址在哪里被引用, 持有者自然浮出水面。
import frida, sys, time, json

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
JS = '''
var base = Process.enumerateModules()[0].base;
var TARGET = base.add(0x27E7360);   // ??_7CCountry@@6B@
rpc.exports.hunt = function (maxHits) {
    var hits = [];
    var ranges = Process.enumerateRanges('rw-');
    var pat = TARGET.toMatchPattern();
    for (var i = 0; i < ranges.length && hits.length < maxHits; i++) {
        var r = ranges[i];
        if (r.size > 256 * 1024 * 1024) continue;
        var found;
        try { found = Memory.scanSync(r.base, r.size, pat); } catch (e) { continue; }
        for (var j = 0; j < found.length && hits.length < maxHits; j++) {
            hits.push(found[j].address.toString());
        }
    }
    return {base: base.toString(), target: TARGET.toString(), count: hits.length, hits: hits};
};
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

pid = frida.spawn([EXE, '-continuelastsave', '-gdpr-compliant'])
session = frida.attach(pid)
sc = session.create_script(JS)
sc.load()
print('[spawn] pid=%d' % pid, flush=True)
frida.resume(pid)
print('[map] = %s' % wait_for_map(), flush=True)
time.sleep(3)
r = sc.exports_sync.hunt(24)
print('[base] %s' % r['base'])
print('[target] %s  (CCountry vtable)' % r['target'])
print('[hits] %d' % r['count'])
for h in r['hits']:
    print('    ' + h)
try: frida.kill(pid)
except Exception: pass