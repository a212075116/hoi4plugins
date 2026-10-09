# frida_country_arrays.py -- 验证 CGameState 里 4 个 size=133 的数组是什么
#
# 来源: 4 字节步长扫描 CGameState 得到的候选数组(此前 8 字节步长全部漏掉),
#       其中 +0x310/+0x370/+0x388/+0x880 的 size 都是 133 = CCountry 实例数。
#
# 要回答的问题:
#   1. 元素是不是 CCountry* (用 vtable 指纹判定, 不靠"看起来像指针")
#   2. 若把下标当 tag 索引, 取出的 Country 是不是"名字与该 tag 对应"
import frida, time

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
JS = '''
var base = Process.enumerateModules()[0].base;
var GS_GLOBAL = base.add(0x332F260);
var VT_COUNTRY = base.add(0x27E7360);
var OFFS = [0x310, 0x370, 0x388, 0x880, 0x2C8, 0x2B0];
function readable(p, n) {
    try {
        var ranges = Process.enumerateRanges('r--');
        for (var i = 0; i < ranges.length; i++) {
            var r = ranges[i];
            if (p.compare(r.base) >= 0 && p.add(n).compare(r.base.add(r.size)) <= 0) return true;
        }
    } catch (e) {}
    return false;
}
function readCString(p) {
    try {
        var size = p.add(16).readU64().toNumber();
        var cap  = p.add(24).readU64().toNumber();
        if (size === 0 || size > 300 || cap > 300 || cap < size) return null;
        var dp = (cap > 15) ? p.readPointer() : p;
        var s = '';
        for (var i = 0; i < size; i++) s += String.fromCharCode(dp.add(i).readU8());
        try { return decodeURIComponent(escape(s)); } catch (e) { return s; }
    } catch (e) { return null; }
}
rpc.exports.run = function () {
    var gs = GS_GLOBAL.readPointer();
    var out = {gs: gs.toString(), arrs: []};
    for (var k = 0; k < OFFS.length; k++) {
        var off = OFFS[k];
        var rec = {off: off, isCountry: 0, notCountry: 0, samples: []};
        var p, sz;
        try { p = gs.add(off).readPointer(); sz = gs.add(off + 8).readU32(); } catch (e) { continue; }
        rec.ptr = p.toString(); rec.size = sz;
        if (sz <= 0 || sz > 20000) { out.arrs.push(rec); continue; }
        for (var i = 0; i < sz; i++) {
            var el;
            try { el = p.add(i * 8).readPointer(); } catch (e) { break; }
            if (el.isNull()) { rec.samples.push({i: i, v: 'null'}); continue; }
            if (!readable(el, 16)) { rec.samples.push({i: i, v: 'unreadable'}); continue; }
            var vt = el.readPointer();
            if (vt.equals(VT_COUNTRY)) {
                rec.isCountry++;
                if (rec.samples.length < 6) {
                    var nm = readCString(el.add(0x10));
                    var ix = el.add(8).readU32();
                    rec.samples.push({i: i, v: 'CCountry', name: nm, idx: ix});
                }
            } else {
                rec.notCountry++;
                if (rec.samples.length < 6) {
                    var delta = vt.sub(base);
                    rec.samples.push({i: i, v: 'other', vtRva: '0x' + delta.toString(16)});
                }
            }
        }
        out.arrs.push(rec);
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
time.sleep(6)
r = sc.exports_sync.run()
print('[CGameState] %s' % r['gs'])
for a in r['arrs']:
    if 'size' not in a: continue
    print('')
    print('+0x%03x  ptr=%s  size=%s   CCountry=%s  其他=%s' % (a['off'], a['ptr'], a['size'], a['isCountry'], a['notCountry']))
    for s in a['samples']:
        if s.get('v') == 'CCountry':
            print('      [%3d] CCountry  idx=%-4s name=%s' % (s['i'], s.get('idx'), s.get('name')))
        else:
            print('      [%3d] %s %s' % (s['i'], s['v'], s.get('vtRva', '')))
try: frida.kill(pid)
except Exception: pass