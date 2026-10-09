# frida_country_owner.py -- 找出 CCountry 数组被谁持有
#
# 先按虚表指纹定位 CCountry 实例(首 8 字节 = 虚表指针), 由实例间距得出对象大小;
# 再拿首个实例地址回搜整个内存, 谁存着这个地址, 谁就是容器。
import frida, time

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
JS = '''
var base = Process.enumerateModules()[0].base;
var VT_COUNTRY = base.add(0x27E7360);
var GS_GLOBAL = base.add(0x332F260);

function rvaOf(p) {
    try {
        var nm = Process.findModuleByAddress(p);
        if (!nm || nm.name !== 'hoi4.exe') return -1;
        return p.sub(base).toInt32() >>> 0;
    } catch (e) { return -1; }
}
function scanWhole(pat, cap) {
    var hits = [];
    var ranges = Process.enumerateRanges('rw-');
    for (var i = 0; i < ranges.length && hits.length < cap; i++) {
        var r = ranges[i];
        if (r.size > 256 * 1024 * 1024) continue;
        var found;
        try { found = Memory.scanSync(r.base, r.size, pat); } catch (e) { continue; }
        for (var j = 0; j < found.length && hits.length < cap; j++) hits.push(found[j].address);
    }
    return hits;
}

rpc.exports.run = function () {
    var out = {};
    // 1. 找 CCountry 实例
    var inst = scanWhole(VT_COUNTRY.toMatchPattern(), 200);
    out.instances = inst.map(function (a) { return a.toString(); });
    if (inst.length >= 2) {
        out.stride = inst[1].sub(inst[0]).toInt32();
    }
    // 2. 拿首个实例地址回搜, 找持有者
    var owners = [];
    if (inst.length > 0) {
        var p0 = inst[0];
        var pat = p0.toMatchPattern();
        var refs = scanWhole(pat, 60);
        for (var k = 0; k < refs.length; k++) owners.push(refs[k].toString());
    }
    out.owners = owners;
    // 3. CGameState 全局当前值
    try { out.gs = GS_GLOBAL.readPointer().toString(); } catch (e) { out.gs = 'err'; }
    return out;
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
r = sc.exports_sync.run()
print('[CGameState] %s' % r.get('gs'))
print('[CCountry 实例数] %d   步长 = %s' % (len(r['instances']), r.get('stride')))
for a in r['instances'][:6]: print('    ' + a)
print('    ... 共 %d 个' % len(r['instances']))
print('[持有首实例地址的位置] %d 处' % len(r.get('owners', [])))
for a in r.get('owners', [])[:20]: print('    ' + a)
try: frida.kill(pid)
except Exception: pass