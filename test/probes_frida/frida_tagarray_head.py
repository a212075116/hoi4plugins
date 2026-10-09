# frida_tagarray_head.py -- dump tag 数组之前的内存, 找它所属对象的头
#
# 上一版确认: 没有任何指针指向 tag 数组基址 => 它是按值内联在某个对象里的。
# 那么数组起点之前应当是同一对象的其它字段(可能含 vtable 或 size)。
#
# 同时: 用 IDA 线索 *(QWORD*)(db+48) / *(DWORD*)(db+60) 反推:
#   若数组内联, 则 db+48 处应是一个指向别处的指针, 而不是数组本身。
#   所以还要在数组附近找"指向 4 字节元素数组"的指针。
import frida, time

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
JS = '''
var base = Process.enumerateModules()[0].base;
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
        while (guard++ < 500) { var pv = s.sub(32); if (!isTagEntry(pv)) break; s = pv; }
        var c = 0, q = s;
        while (c < 500 && isTagEntry(q)) { c++; q = q.add(32); }
        if (c > 50) { arrStart = s; arrCount = c; }
    }
    if (!arrStart) return {err: 'no array'};
    var out = {arr: arrStart.toString(), count: arrCount, head: null, tail: null, nearPtrs: []};
    // 头 512 字节
    var hb;
    try { hb = new Uint8Array(arrStart.sub(512).readByteArray(512)); } catch (e) { return {err: 'head read ' + e}; }
    var hx = [];
    for (var i = 0; i < hb.length; i++) hx.push(('0' + hb[i].toString(16)).slice(-2));
    out.head = hx.join('');
    out.headStart = arrStart.sub(512).toString();
    // 数组之后 128 字节
    var tb;
    try { tb = new Uint8Array(arrStart.add(arrCount * 32).readByteArray(128)); } catch (e) { tb = null; }
    if (tb) {
        var tx = [];
        for (var i = 0; i < tb.length; i++) tx.push(('0' + tb[i].toString(16)).slice(-2));
        out.tail = tx.join('');
        out.tailStart = arrStart.add(arrCount * 32).toString();
    }
    // 在头 512 字节里找形如指针的 8 字节值
    var hs = arrStart.sub(512);
    for (var o = 0; o < 512 - 8; o += 8) {
        var v;
        try { v = hs.add(o).readPointer(); } catch (e) { continue; }
        if (v.isNull()) continue;
        var isHeap = false;
        for (var z = 0; z < rs.length; z++) {
            if (rs[z].protection.indexOf('rw') >= 0 && v.compare(rs[z].base) >= 0 && v.compare(rs[z].base.add(rs[z].size)) < 0) { isHeap = true; break; }
        }
        if (!isHeap) continue;
        var note = '';
        try {
            var vt = v.readPointer();
            var d = vt.sub(base);
            if (d.compare(0) > 0 && d.compare(0x4000000) < 0) note = 'vtRva=0x' + d.toString(16);
        } catch (e) {}
        out.nearPtrs.push({off: '-' + (512 - o), val: v.toString(), note: note});
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
else:
    print('[tag 数组] %s  项数=%d' % (r['arr'], r['count']))
    print('[数组之后 128 字节 @ %s]' % r.get('tailStart'))
    if r.get('tail'):
        t = r['tail']
        for i in range(0, len(t), 32):
            print('    %s' % ' '.join(t[j:j+2] for j in range(i, min(i+32, len(t)), 2)))
    print('')
    print('[数组之前 512 字节 @ %s]' % r.get('headStart'))
    h = r['head']
    for i in range(0, len(h), 32):
        chunk = h[i:i+32]
        bys = [chunk[j:j+2] for j in range(0, len(chunk), 2)]
        asc = ''.join(chr(int(x, 16)) if 32 <= int(x, 16) < 127 else '.' for x in bys)
        print('    +%03x  %s  %s' % (i, ' '.join(bys), asc))
    print('')
    print('[头 512 字节里像堆指针的 8 字节值] %d 个' % len(r['nearPtrs']))
    for p in r['nearPtrs']:
        print('    arr%5s   %s   %s' % (p['off'], p['val'], p.get('note', '')))
try: frida.kill(pid)
except Exception: pass