# frida_find_name_field.py -- 扫 CProvince / CState 对象里所有 CString 候选, 找名字字段
#
# 背景: +0x40 不是名字(实际是空 CString)。
# CString 的判据(此前已多次验证): 32 字节, {数据@+0, size@+0x10, cap@+0x18},
#   cap == 15 表示内联(数据就在 +0 起 16 字节内), cap > 15 时 +0 处是堆指针。
#
# 本脚本对每个对象扫 0..0x300, 对每个 8 字节对齐偏移检查是否构成合法 CString,
# 并把可读文本内容打印出来。不做过滤, 所有候选都列。
import frida, time

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
JS = '''
var mods = Process.enumerateModules();
var exe = null;
for (var i = 0; i < mods.length; i++) if (mods[i].name.toLowerCase() === 'hoi4.exe') exe = mods[i];
var base = exe.base;
var GS_GLOBAL = base.add(0x332F260);
var rs = null;
function readable(p, n) {
    if (!rs) rs = Process.enumerateRanges('r--');
    for (var i = 0; i < rs.length; i++) {
        var r = rs[i];
        if (p.compare(r.base) >= 0 && p.add(n).compare(r.base.add(r.size)) <= 0) return true;
    }
    return false;
}
function tryCString(p) {
    try {
        var sz = Number(p.add(16).readU64());
        var cap = Number(p.add(24).readU64());
        if (cap < sz) return null;
        if (sz > 200) return null;
        if (cap > 200) return null;
        var dp = (cap > 15) ? p.readPointer() : p;
        if (!readable(dp, Math.max(sz, 1))) return null;
        var s = '';
        for (var i = 0; i < sz; i++) {
            var c = dp.add(i).readU8();
            s += (c >= 32 && c < 127) ? String.fromCharCode(c) : '?';
        }
        return {size: sz, cap: cap, text: s, inline: cap <= 15};
    } catch (e) { return null; }
}
rpc.exports.run = function () {
    var gs = GS_GLOBAL.readPointer();
    var out = {prov: [], state: []};
    function scan(ptr, size, key, nObj) {
        var pProv = ptr;
        var objs = [];
        for (var i = 1; i <= nObj; i++) {
            var p;
            try { p = pProv.add(i * 8).readPointer(); } catch (e) { break; }
            if (!p.isNull() && readable(p, 0x300)) objs.push({i: i, p: p});
        }
        // 收集每个偏移上的 CString 候选
        for (var off = 0; off < 0x300; off += 8) {
            var recs = [];
            var nonEmpty = 0;
            for (var k = 0; k < objs.length; k++) {
                var cs = tryCString(objs[k].p.add(off));
                recs.push(cs);
                if (cs && cs.size > 0) nonEmpty++;
            }
            if (nonEmpty === 0) continue;
            out[key].push({off: off, nonEmpty: nonEmpty, total: objs.length, samples: recs});
        }
    }
    scan(gs.add(0x2B0).readPointer(), gs.add(0x2B0).add(8).readU32(), 'prov', 8);
    scan(gs.add(0x2C8).readPointer(), gs.add(0x2C8).add(8).readU32(), 'state', 8);
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
for key, label in (('prov', 'CProvince'), ('state', 'CState')):
    print('')
    print('=== %s 里的非空 CString 候选 ===' % label)
    if not r[key]:
        print('    (无)')
        continue
    for c in r[key]:
        print('')
        print('  +0x%-4x  非空 %d/%d' % (c['off'], c['nonEmpty'], c['total']))
        for s in c['samples']:
            if s and s['size'] > 0:
                print('        size=%-4d cap=%-4d inline=%-5s %r' % (s['size'], s['cap'], s['inline'], s['text']))
            else:
                print('        (空)')
try: frida.kill(pid)
except Exception: pass