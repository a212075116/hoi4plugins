# frida_find_aby.py -- 搜内存里的 ABY, 定位 tag 的真实存放处
#
# ABY 只属于一个国家(玩家国家), 因此它的出现位置最干净, 不会被局部化键名污染。
# 找到后看它落在什么对象里, tag 的存放方式就确定了。
import frida, time

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
JS = '''
var base = Process.enumerateModules()[0].base;
var VT_COUNTRY = base.add(0x27E7360);
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
function readCString(p) {
    try {
        var size = p.add(16).readU64().toNumber();
        var cap  = p.add(24).readU64().toNumber();
        if (size === 0 || size > 300 || cap > 300 || cap < size) return null;
        var dataP = (cap > 15) ? p.readPointer() : p;
        var s = '';
        for (var i = 0; i < size; i++) s += String.fromCharCode(dataP.add(i).readU8());
        try { return decodeURIComponent(escape(s)); } catch (e) { return s; }
    } catch (e) { return null; }
}
rpc.exports.run = function () {
    var out = {};
    var hits = scanWhole('41 42 59', 60);   // 'ABY'
    out.n = hits.length;
    out.ctx = [];
    for (var i = 0; i < hits.length; i++) {
        var a = hits[i];
        var b = '';
        for (var k = -6; k < 14; k++) {
            var v;
            try { v = a.add(k).readU8(); } catch (e) { v = 0x3f; }
            b += (v >= 0x20 && v < 0x7f) ? String.fromCharCode(v) : '.';
        }
        var exe = Process.findModuleByAddress(a);
        out.ctx.push({at: a.toString(), near: b, mod: exe ? exe.name : 'heap'});
    }
    // 这些位置是否落进 CCountry 实例
    var inst = scanWhole(VT_COUNTRY.toMatchPattern(), 400);
    var inC = [];
    for (var i2 = 0; i2 < inst.length; i2++) {
        for (var j = 0; j < hits.length; j++) {
            var d = hits[j].sub(inst[i2]).toInt32();
            if (d >= 0 && d < 6000) {
                inC.push({obj: inst[i2].toString(), off: d, name: readCString(inst[i2].add(0x10))});
            }
        }
    }
    out.inCountry = inC;
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
print('[ABY 出现] %d 处' % r['n'])
for c in r['ctx'][:25]:
    print('    %s  [%s]  \"%s\"' % (c['at'], c['mod'], c['near']))
print('[落在 CCountry 实例内的] %d 处' % len(r['inCountry']))
for x in r['inCountry']:
    print('    obj %s  +0x%x   name=%s' % (x['obj'], x['off'], x['name']))
try: frida.kill(pid)
except Exception: pass