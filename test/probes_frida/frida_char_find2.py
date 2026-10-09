# frida_char_find2.py -- 一次扫描同时拿 CCharacter 实例与持有者
#
# 上一版太慢: 对 400 个对象各自扫一遍全内存 => O(n) 次全内存扫描。
# 本版改为单遍扫描: 对每个 8 字节位置, 同时判断
#   (a) 该位置是否是 CCharacter 对象头 (值 == 虚表 且 +0x48 是合法名字 CString)
#   (b) 该位置的值是否指向一个已知的 CCharacter 对象 (即持有者)
#
# 静态依据: 虚表 RVA 0x297EA60, 对象大小 0x130, 名字在 +0x48, int 在 +0x70
import frida, time

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
JS = '''
var mods = Process.enumerateModules();
var exe = null;
for (var i = 0; i < mods.length; i++) if (mods[i].name.toLowerCase() === 'hoi4.exe') exe = mods[i];
var base = exe.base;
var VT_CHAR = base.add(0x297EA60);
var rs = null;
function readable(p, n) {
    if (!rs) rs = Process.enumerateRanges('r--');
    for (var i = 0; i < rs.length; i++) {
        var r = rs[i];
        if (p.compare(r.base) >= 0 && p.add(n).compare(r.base.add(r.size)) <= 0) return true;
    }
    return false;
}
function readCS(p) {
    try {
        var sz = Number(p.add(16).readU64());
        var cap = Number(p.add(24).readU64());
        if (sz === 0 || sz > 100 || cap < sz || cap > 100) return null;
        var dp = (cap > 15) ? p.readPointer() : p;
        if (!readable(dp, sz)) return null;
        var s = '';
        for (var i = 0; i < sz; i++) {
            var c = dp.add(i).readU8();
            if (c < 32 || c > 126) return null;
            s += String.fromCharCode(c);
        }
        return s;
    } catch (e) { return null; }
}
rpc.exports.run = function () {
    var wr = Process.enumerateRanges('rw-');
    var pat = VT_CHAR.toMatchPattern();
    var out = {vtChar: VT_CHAR.toString(), ranges: wr.length, rawHits: 0,
               objs: [], samples: [], holders: [], holderCount: 0};
    var raw = [];
    // 第一遍: 单次全内存扫描, 找到所有虚表值出现的位置
    for (var i = 0; i < wr.length; i++) {
        var r = wr[i];
        if (r.size > 256 * 1024 * 1024) continue;
        var hits;
        try { hits = Memory.scanSync(r.base, r.size, pat); } catch (e) { continue; }
        for (var j = 0; j < hits.length; j++) raw.push(hits[j].address);
    }
    out.rawHits = raw.length;
    // 第二遍: 用强判据筛, 同时记下每个对象地址(用于判持有者)
    var objs = [];
    for (var k = 0; k < raw.length; k++) {
        var a = raw[k];
        if (!readable(a, 0x130)) continue;
        var nm = readCS(a.add(0x48));
        if (nm === null) continue;
        objs.push({p: a, name: nm});
    }
    out.strongHits = objs.length;
    for (var k = 0; k < objs.length; k++) {
        if (objs[k].name.length > 0) {
            out.objCount = (out.objCount || 0) + 1;
            if (out.samples.length < 30) {
                var idv = null;
                try { idv = objs[k].p.add(0x70).readU32(); } catch (e) {}
                out.samples.push({at: objs[k].p.toString(), name: objs[k].name, id70: idv});
            }
        }
    }
    // 第三遍: 建立对象地址 -> 名字 的字符串集合, 一次扫描找持有者
    var want = {};
    for (var k = 0; k < objs.length; k++) want[objs[k].p.toString()] = objs[k].name;
    for (var i = 0; i < wr.length; i++) {
        var r = wr[i];
        if (r.size > 256 * 1024 * 1024) continue;
        var n = Math.floor(r.size / 8);
        for (var q = 0; q < n; q++) {
            var p = r.base.add(q * 8);
            var v;
            try { v = p.readPointer(); } catch (e) { continue; }
            var ks = v.toString();
            if (want[ks] !== undefined) {
                out.holderCount++;
                if (out.holders.length < 30) {
                    out.holders.push({holder: p.toString(), obj: ks, name: want[ks], seg: r.base.toString()});
                }
            }
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
time.sleep(8)
r = sc.exports_sync.run()
print('')
print('CCharacter 虚表        : %s' % r['vtChar'])
print('可写段数               : %d' % r['ranges'])
print('原始命中(只比虚表)     : %d' % r['rawHits'])
print('强判据命中(虚表+CString): %d' % r['strongHits'])
print('其中有非空名字的        : %s' % r.get('objCount'))
print('指向对象的指针总数      : %d' % r['holderCount'])
print('')
print('=== 样本 ===')
for s in r['samples']:
    print('    %-20s name=%-30s id70=%s' % (s['at'], s['name'], s['id70']))
print('')
print('=== 持有者位置(前 30) ===')
if not r['holders']: print('    (无)')
for h in r['holders']:
    print('    持有者 %-20s -> 对象 %-20s (name=%s)' % (h['holder'], h['obj'], h['name']))
try: frida.kill(pid)
except Exception: pass