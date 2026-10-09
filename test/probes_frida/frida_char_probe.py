# frida_char_probe.py -- dump CCharacter 命中点的真实上下文, 查清 +8 = 0x49 的来源
#
# 已查清: Invalid_country_tag_0 的值是 0xFFFFFFFF (4 字节 CCountryTag 的无效值),
# 所以构造函数里 *(_QWORD*)(a1+8) = Invalid_country_tag_0 是"写入 0xFFFFFFFF"。
# 那动态扫出来的 +8 = 0x49('I') 就说明: 扫到的位置并不是对象头。
#
# 本脚本:
#   1. 确认 hoi4.exe 的 base 与 CCharacter 虚表的绝对地址
#   2. dump 命中点前后 64 字节, 看它到底落在什么结构里
#   3. 换一个更强的对象头判据: 要求 +8 是合法 tag 或 0xFFFFFFFF, 再统计命中数
import frida, time

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
JS = '''
var mods = Process.enumerateModules();
var exe = null;
for (var i = 0; i < mods.length; i++) {
    if (mods[i].name.toLowerCase() === 'hoi4.exe') { exe = mods[i]; break; }
}
var base = (exe ? exe.base : mods[0].base);
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
function hex(p, n) {
    try {
        var b = new Uint8Array(p.readByteArray(n));
        var s = [];
        for (var i = 0; i < b.length; i++) s.push(('0' + b[i].toString(16)).slice(-2));
        return s.join(' ');
    } catch (e) { return 'ERR'; }
}
rpc.exports.run = function () {
    var out = {exeName: exe ? exe.name : '(not found)', exeBase: base.toString(),
               vtChar: VT_CHAR.toString(), ranges: [], dumps: [], stats: null};
    // 只看可写段
    var wr = Process.enumerateRanges('rw-');
    out.rangeCount = wr.length;
    var dumps = 0;
    var okTag = 0, okInvalid = 0, other = 0;
    var pat = VT_CHAR.toMatchPattern();
    for (var i = 0; i < wr.length; i++) {
        var r = wr[i];
        if (r.size > 512 * 1024 * 1024) continue;
        var hits;
        try { hits = Memory.scanSync(r.base, r.size, pat); } catch (e) { continue; }
        for (var j = 0; j < hits.length; j++) {
            var a = hits[j].address;
            if (!readable(a, 0x40)) continue;
            var raw8;
            try { raw8 = a.add(8).readU32(); } catch (e) { continue; }
            var isInvalid = (raw8 === 0xFFFFFFFF);
            var b = null;
            try { b = new Uint8Array(a.add(8).readByteArray(4)); } catch (e) {}
            var isTag = b && b[3] === 0 && b[0] >= 65 && b[0] <= 90 && b[1] >= 65 && b[1] <= 90 && b[2] >= 65 && b[2] <= 90;
            if (isInvalid) okInvalid++;
            else if (isTag) okTag++;
            else other++;
            if (dumps < 6) {
                out.dumps.push({at: a.toString(), pre: hex(a.sub(16), 16), post: hex(a.add(16), 48)});
                dumps++;
            }
        }
    }
    out.stats = {validTag: okTag, invalid: okInvalid, other: other};
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
print('[模块] %s  base=%s' % (r['exeName'], r['exeBase']))
print('[CCharacter 虚表绝对地址] %s' % r['vtChar'])
print('[可写段数] %d' % r['rangeCount'])
print('')
print('=== 命中点上下文 dump (前16字节 | 命中点起48字节) ===')
for d in r['dumps']:
    print('  @%s' % d['at'])
    print('    pre : %s' % d['pre'])
    def fmt(h):
        parts = h.split(' ')
        rows = []
        for k in range(0, len(parts), 16):
            rows.append(' '.join(parts[k:k+16]))
        return '\n           '.join(rows)
    print('    post: %s' % fmt(d['post']))
    print('')
print('=== +0x08 值的分类统计 ===')
s = r['stats']
print('    合法 tag(3字母+00) : %d' % s['validTag'])
print('    0xFFFFFFFF(无效)   : %d' % s['invalid'])
print('    其它               : %d' % s['other'])
try: frida.kill(pid)
except Exception: pass