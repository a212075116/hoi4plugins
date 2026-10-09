# frida_char_find.py -- 用强判据扫堆找 CCharacter 实例
#
# 静态依据(本轮 IDA 分析得到):
#   虚表 RVA 0x297EA60
#   对象大小 0x130  (来自 sub_140FA0A20 与 sub_1406B7260 里的 malloc(0x130))
#   构造函数 sub_140F9EC50(this, name, intId):
#     +0x18 = 357 (初值)   +0x28 起 CString(清空)   +0x48 起 CString <- name
#     +0x70 = intId
#   调用者 sub_1406B7260 会把这个 name 里的 空格/-/' 替换为 _
#
# 判据(比上一轮严格): 位置 p 必须同时满足
#   1. *(void**)p == hoi4.exe + 0x297EA60        虚表精确相等
#   2. p + 0x48 处构成合法 CString(0 < size <= 100, cap >= size, 数据可读)
# 只满足 1 不算 —— 上一轮就是只看 1, 结果 3749 个命中里几乎没有真对象。
import frida, time

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
JS = '''
var mods = Process.enumerateModules();
var exe = null;
for (var i = 0; i < mods.length; i++) if (mods[i].name.toLowerCase() === 'hoi4.exe') exe = mods[i];
var base = exe.base;
var GS_GLOBAL = base.add(0x332F260);
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
        if (sz === 0 || sz > 100) return null;
        if (cap < sz || cap > 100) return null;
        var dp = (cap > 15) ? p.readPointer() : p;
        if (!readable(dp, sz)) return null;
        var s = '';
        for (var i = 0; i < sz; i++) {
            var c = dp.add(i).readU8();
            if (c < 32 || c > 126) return null;   // 必须是可打印 ASCII
            s += String.fromCharCode(c);
        }
        return s;
    } catch (e) { return null; }
}
rpc.exports.run = function () {
    var wr = Process.enumerateRanges('rw-');
    var pat = VT_CHAR.toMatchPattern();
    var out = {vtChar: VT_CHAR.toString(), ranges: wr.length,
               rawHits: 0, strongHits: 0, withName: 0, samples: [], holders: []};
    var objs = [];
    for (var i = 0; i < wr.length; i++) {
        var r = wr[i];
        if (r.size > 256 * 1024 * 1024) continue;
        var hits;
        try { hits = Memory.scanSync(r.base, r.size, pat); } catch (e) { continue; }
        for (var j = 0; j < hits.length; j++) {
            var a = hits[j].address;
            out.rawHits++;
            if (!readable(a, 0x130)) continue;
            var nm = readCS(a.add(0x48));
            if (nm === null) continue;
            out.strongHits++;
            if (nm.length > 0) {
                out.withName++;
                if (objs.length < 400) objs.push(a);
                if (out.samples.length < 25) {
                    var idv = null;
                    try { idv = a.add(0x70).readU32(); } catch (e) {}
                    out.samples.push({at: a.toString(), name: nm, id70: idv});
                }
            }
        }
    }
    // 找谁持有这些对象(容器)
    for (var k = 0; k < objs.length && out.holders.length < 20; k++) {
        var op = objs[k];
        var p2 = op.toMatchPattern();
        for (var i = 0; i < wr.length; i++) {
            var r = wr[i];
            if (r.size > 256 * 1024 * 1024) continue;
            var hs;
            try { hs = Memory.scanSync(r.base, r.size, p2); } catch (e) { continue; }
            for (var j = 0; j < hs.length; j++) {
                out.holders.push({obj: op.toString(), holder: hs[j].address.toString(), rangeBase: r.base.toString(), rangeSize: r.size});
                if (out.holders.length >= 20) break;
            }
            if (out.holders.length >= 20) break;
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
print('CCharacter 虚表: %s' % r['vtChar'])
print('可写段数       : %d' % r['ranges'])
print('')
print('原始命中(只比虚表)     : %d' % r['rawHits'])
print('强判据命中(虚表+CString): %d' % r['strongHits'])
print('其中有非空名字的        : %d' % r['withName'])
print('')
print('=== 样本(名字 / +0x70) ===')
for s in r['samples']:
    print('    %-20s name=%-28s id70=%s' % (s['at'], s['name'], s['id70']))
print('')
print('=== 指向这些对象的持有者(找容器) ===')
if not r['holders']:
    print('    (无)')
for h in r['holders']:
    print('    对象 %-20s <- 持有者 %-20s (段 %s +%d)' % (h['obj'], h['holder'], h['rangeBase'], h['rangeSize']))
try: frida.kill(pid)
except Exception: pass