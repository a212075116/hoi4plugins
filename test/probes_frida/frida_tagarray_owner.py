# frida_tagarray_owner.py -- 找到持有 tag 数组指针的那个对象/偏移
#
# 现状: tag 数组已完全验证(132 项 CString, size==3 cap==15), 但它的地址是堆地址, 每次运行都变。
# 需要一条稳定寻址路径。
#
# 线索: IDA 反编译 sub_14071BD10 用 *(QWORD*)(db+48) 取数组基址, *(DWORD*)(db+60) 取大小。
# 所以只要找到 db(国家数据库对象), 或找到任何持有该数组指针的地方, 就能稳定寻址。
#
# 做法: 定位数组后, 在 CGameState 范围内以及全内存里搜"指向该数组的指针"。
import frida, time, re

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
    // 找数组起点: 向后扫描, 第一项是 3 大写字母+00 且 size==3 cap==15
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
        // 向前找起点
        var s = a;
        var guard = 0;
        while (guard++ < 500) {
            var prev = s.sub(32);
            if (!isTagEntry(prev)) break;
            s = prev;
        }
        // 计数
        var c = 0;
        var q = s;
        while (c < 500 && isTagEntry(q)) { c++; q = q.add(32); }
        if (c > 50) { arrStart = s; arrCount = c; }
    }
    if (!arrStart) return {err: 'no array'};
    var out = {arr: arrStart.toString(), count: arrCount, holders: [], gs: null};
    // 全内存搜指向 arrStart 的指针
    var needle = arrStart.toString().replace('0x', '');
    var le = [];
    for (var i = 7; i >= 0; i--) {
        var byteVal = parseInt(needle.substr(i * 2 || i * 2, 2), 16);
        if (isNaN(byteVal)) byteVal = 0;
    }
    // 用 ArrayBuffer 手工构造小端字节序列
    var tmp = new ArrayBuffer(8);
    var dv = new DataView(tmp);
    dv.setBigUint64(0, arrStart, true);
    var bytes = new Uint8Array(tmp);
    var pat = [];
    for (var i = 0; i < 8; i++) pat.push(('0' + bytes[i].toString(16)).slice(-2));
    var patStr = pat.join(' ');
    var ptrHits = [];
    for (var i = 0; i < rs.length && ptrHits.length < 100; i++) {
        var r = rs[i];
        if (r.size > 256 * 1024 * 1024) continue;
        var res2;
        try { res2 = Memory.scanSync(r.base, r.size, patStr); } catch (e) { continue; }
        for (var j = 0; j < res2.length && ptrHits.length < 100; j++) ptrHits.push(res2[j].address);
    }
    out.holders = ptrHits.map(function (p) { return p.toString(); });
    // 看这些持有者相对 CGameState 的偏移
    var gs = GS_GLOBAL.readPointer();
    out.gs = gs.toString();
    for (var m = 0; m < ptrHits.length; m++) {
        var d = ptrHits[m].sub(gs);
        if (d.compare(0) >= 0 && d.compare(0x20000) < 0) {
            out.gsOff = '0x' + d.toString(16);
            break;
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
time.sleep(6)
r = sc.exports_sync.run()
if 'err' in r:
    print('[错误] %s' % r['err'])
else:
    print('[tag 数组] %s   项数=%d' % (r['arr'], r['count']))
    print('[CGameState] %s' % r['gs'])
    if r.get('gsOff'):
        print('[在 CGameState 内的偏移] %s   <= 稳定寻址路径' % r['gsOff'])
    else:
        print('[不在 CGameState 内]')
    print('[持有该数组指针的位置] %d 个' % len(r['holders']))
    for h in r['holders'][:15]:
        # 标注是否在 CGameState 附近
        extra = ''
        try:
            hv = int(h, 16); gv = int(r['gs'], 16)
            if 0 <= hv - gv < 0x20000: extra = '  (CGameState + 0x%x)' % (hv - gv)
        except Exception: pass
        print('    %s%s' % (h, extra))
try: frida.kill(pid)
except Exception: pass