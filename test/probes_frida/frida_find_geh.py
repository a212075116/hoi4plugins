# frida_find_geh.py -- 全内存搜 tag 字节 GEH, 看它究竟存在哪
#
# 既然"格黑娜学园"实例里没有 GEH, 那就反过来: 先找到 GEH 在哪里出现,
# 再看那些位置落在什么对象里, tag 的存放方式自然清楚。
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
        if (size > 512 || cap > 512 || cap < size || size === 0) return null;
        var dataP = (cap > 15) ? p.readPointer() : p;
        var s = '';
        for (var i = 0; i < size; i++) s += String.fromCharCode(dataP.add(i).readU8());
        try { return decodeURIComponent(escape(s)); } catch (e) { return s; }
    } catch (e) { return null; }
}
rpc.exports.run = function () {
    var out = {};
    // 1. GEH 在哪些位置出现
    var hits = scanWhole('47 45 48', 40);
    out.geh = hits.map(function (a) { return a.toString(); });
    // 2. CCountry 首实例地址(用于比对: tag 是否出现在国家对象附近)
    var inst = scanWhole(VT_COUNTRY.toMatchPattern(), 400);
    out.nCountry = inst.length;
    out.countryFirst = inst.length ? inst[0].toString() : null;
    // 3. 每个 GEH 位置周围 16 字节上下文
    out.ctx = [];
    for (var i = 0; i < hits.length && i < 12; i++) {
        var a = hits[i];
        var ctx = '';
        for (var k = -8; k < 16; k++) {
            try { ctx += ('0' + a.add(k).readU8().toString(16)).slice(-2); } catch (e) { ctx += '??'; }
            ctx += (k === -1 ? '|' : ' ');
        }
        out.ctx.push({at: a.toString(), bytes: ctx});
    }
    // 4. 这些位置是否落在某个 CCountry 实例里
    out.inCountry = [];
    for (var i = 0; i < inst.length; i++) {
        for (var j = 0; j < hits.length; j++) {
            var d = hits[j].sub(inst[i]).toInt32();
            if (d >= 0 && d < 6000) out.inCountry.push({obj: inst[i].toString(), off: d, tag: hits[j].toString()});
        }
    }
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
print('[CCountry 实例数] %s   首实例 %s' % (r['nCountry'], r['countryFirst']))
print('[GEH 出现位置] %d 处' % len(r['geh']))
for i, a in enumerate(r['geh'][:12]):
    ctx = r['ctx'][i]['bytes'] if i < len(r['ctx']) else ''
    print('    %s   %s' % (a, ctx))
print('[落在某个 CCountry 实例内的] %d 处' % len(r['inCountry']))
for x in r['inCountry'][:12]:
    print('    obj %s  +0x%x' % (x['obj'], x['off']))
try: frida.kill(pid)
except Exception: pass