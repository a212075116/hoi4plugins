# frida_tagarray_owner2.py -- 修正搜索: 用 NativePointer.toMatchPattern()
#
# 上一版 0 命中的原因: 手工用 DataView.setBigUint64 构造小端模式,
# 而它需要 BigInt 参数, 导致模式串不对(错误被 try 吞掉)。
# Frida 的 NativePointer 自带 toMatchPattern(), 直接用它。
#
# 目标: 找到持有 tag 数组基址的指针, 从而得到稳定寻址路径。
import frida, time

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
JS = '''
var base = Process.enumerateModules()[0].base;
var GS_GLOBAL = base.add(0x332F260);
rpc.exports.run = function () {
    var rs = Process.enumerateRanges('rw-');
    var hits = [];
    for (var i = 0; i < rs.length && hits.length < 3000; i++) {
        var r = rs[i];
        if (r.size > 128 * 1024 * 1024) continue;
        var res;
        try { res = Memory.scanSync(r.base, r.size, '41 42 59 00'); } catch (e) { continue; }
        for (var j = 0; j < res.length && hits.length < 3000; j++) hits.push(res[j].address);
    }
    function isTagEntry(p) {
        try {
            var b = new Uint8Array(p.readByteArray(32));
            var s = String.fromCharCode(b[0], b[1], b[2]);
            if (!/^[A-Z0-9]{3}$/.test(s) || b[3] !== 0) return null;
            if (Number(p.add(16).readU64()) !== 3) return null;
            if (Number(p.add(24).readU64()) !== 15) return null;
            return s;
        } catch (e) { return null; }
    }
    var arrStart = null, arrCount = 0;
    for (var k = 0; k < hits.length && !arrStart; k++) {
        var a = hits[k];
        var s = a, guard = 0;
        while (guard++ < 500) {
            var prev = s.sub(32);
            if (!isTagEntry(prev)) break;
            s = prev;
        }
        var c = 0, q = s;
        while (c < 500 && isTagEntry(q)) { c++; q = q.add(32); }
        if (c > 50) { arrStart = s; arrCount = c; }
    }
    if (!arrStart) return {err: 'no array'};
    var out = {arr: arrStart.toString(), count: arrCount, holders: []};
    // 用 toMatchPattern 搜指针
    var pat;
    try { pat = arrStart.toMatchPattern(); } catch (e) { return {err: 'toMatchPattern: ' + e, arr: arrStart.toString()}; }
    out.pattern = pat;
    var ptrHits = [];
    for (var i = 0; i < rs.length && ptrHits.length < 100; i++) {
        var r = rs[i];
        if (r.size > 256 * 1024 * 1024) continue;
        var res2;
        try { res2 = Memory.scanSync(r.base, r.size, pat); } catch (e) { continue; }
        for (var j = 0; j < res2.length && ptrHits.length < 100; j++) ptrHits.push(res2[j].address);
    }
    var gs = GS_GLOBAL.readPointer();
    out.gs = gs.toString();
    for (var m = 0; m < ptrHits.length; m++) {
        var p = ptrHits[m];
        var rec = {at: p.toString()};
        var d = p.sub(gs);
        if (d.compare(0) >= 0 && d.compare(0x40000) < 0) rec.gsOff = '0x' + d.toString(16);
        // 看它前后 32 字节里有没有 size/cap 模式
        try {
            rec.after1 = p.add(8).readU64().toString();
            rec.after2 = p.add(16).readU64().toString();
        } catch (e) {}
        out.holders.push(rec);
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
if 'err' in r:
    print('[错误] %s' % r['err'])
    if 'arr' in r: print('[数组] %s' % r['arr'])
else:
    print('[tag 数组] %s  项数=%d' % (r['arr'], r['count']))
    print('[指针模式] %s' % r['pattern'])
    print('[CGameState] %s' % r['gs'])
    print('[持有者] %d 个' % len(r['holders']))
    for h in r['holders'][:20]:
        extra = ('  (CGameState + %s)' % h['gsOff']) if h.get('gsOff') else ''
        extra += '   after: %s %s' % (h.get('after1'), h.get('after2'))
        print('    %s%s' % (h['at'], extra))
try: frida.kill(pid)
except Exception: pass