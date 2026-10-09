# frida_tagentry.py -- 确认 tag 数组每项的 32 字节结构
#
# 已确认: 数组项间距 32 字节, 每项头 4 字节是 tag。
# 假说: 每项是一个 CString(MSVC std::string, 32 字节):
#   +0x00  16 字节内联数据  (短 tag 就地存放, 如 "ABY" + 00)
#   +0x10  size_t size
#   +0x18  size_t capacity  (内联应为 15)
# 判据(可证伪): 若假说成立, 则每项 +0x10 == 3 且 +0x18 == 15。
#               若不成立, 该假说即被否证。
#
# 同时验证: 数组下标 i 是否等于 CCountry+0x08 的索引。
import frida, time, re

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
JS = '''
var base = Process.enumerateModules()[0].base;
var GS_GLOBAL = base.add(0x332F260);
var VT_COUNTRY = base.add(0x27E7360);
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
    // 选簇: 附近同时有 GEH 与 HYA 的那个
    var best = null;
    for (var k = 0; k < hits.length; k++) {
        var a = hits[k];
        var st = a.sub(2048);
        var ok = 0;
        var buf;
        try { buf = st.readByteArray(4096); } catch (e) { continue; }
        var u = new Uint8Array(buf);
        var keys = ['GEH','HYA','SRT','KRO','MIL'];
        for (var n = 0; n < keys.length; n++) {
            var t = keys[n];
            for (var off = 0; off + 4 <= u.length; off += 32) {
                if (u[off]===t.charCodeAt(0) && u[off+1]===t.charCodeAt(1) && u[off+2]===t.charCodeAt(2) && u[off+3]===0) { ok++; break; }
            }
        }
        if (!best || ok > best.ok) best = {aby: a, st: st, ok: ok};
    }
    if (!best) return {err: 'no cluster'};
    var out = {aby: best.aby.toString(), st: best.st.toString(), ok: best.ok, items: []};
    // 从窗口起点向后, 按 32 字节步长扫描, 找数组真正的起点
    // 真起点: 第一项是 3 个大写字母 + 00
    var arrStart = null;
    for (var off = 0; off + 32 <= 4096; off += 32) {
        var p = best.st.add(off);
        var b;
        try { b = new Uint8Array(p.readByteArray(32)); } catch (e) { break; }
        var s = String.fromCharCode(b[0], b[1], b[2]);
        var isTag = /^[A-Z0-9]{3}$/.test(s) && b[3] === 0;
        var sz = 0, cap = 0;
        try { sz = Number(p.add(16).readU64()); cap = Number(p.add(24).readU64()); } catch (e) {}
        if (isTag && arrStart === null) arrStart = p;
    }
    out.arrStart = arrStart ? arrStart.toString() : null;
    if (arrStart) {
        // 逐项导出
        for (var i = 0; i < 140; i++) {
            var p2 = arrStart.add(i * 32);
            var b2;
            try { b2 = new Uint8Array(p2.readByteArray(32)); } catch (e) { break; }
            var s2 = String.fromCharCode(b2[0], b2[1], b2[2]);
            var okTag = /^[A-Z0-9]{3}$/.test(s2) && b2[3] === 0;
            var sz2 = 0, cap2 = 0;
            try { sz2 = Number(p2.add(16).readU64()); cap2 = Number(p2.add(24).readU64()); } catch (e) {}
            out.items.push({i: i, tag: okTag ? s2 : null, raw0: Array.from(b2.slice(0,4)), size: sz2, cap: cap2, addr: p2.toString()});
        }
    }
    // 顺便: CGameState + 0x310 是否指向同一批 CCountry
    var gs = GS_GLOBAL.readPointer();
    var arr = gs.add(0x310).readPointer();
    out.gsArr = arr.toString();
    var idxs = [];
    for (var m = 0; m < 6; m++) {
        var el = arr.add(m * 8).readPointer();
        idxs.push({i: m, idx: el.add(8).readU32(), vtOk: el.readPointer().equals(VT_COUNTRY)});
    }
    out.gsSamples = idxs;
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
    print('[数组起点] %s   ABY@%s' % (r['arrStart'], r['aby']))
    print('')
    print('[逐项 32 字节结构]  (判据: size 应=3, cap 应=15)')
    nsz = 0; ncap = 0; ntag = 0
    for it in r['items']:
        if it['tag'] is None: continue
        ntag += 1
        if it['size'] == 3: nsz += 1
        if it['cap'] == 15: ncap += 1
    print('    有效 tag 项: %d   size==3 的: %d   cap==15 的: %d' % (ntag, nsz, ncap))
    print('')
    for it in r['items'][:45]:
        t = it['tag'] if it['tag'] else ('[%02x %02x %02x %02x]' % tuple(it['raw0']))
        print('    [%3d] %-12s size=%-6s cap=%-6s %s' % (it['i'], t, it['size'], it['cap'], it['addr']))
    print('')
    print('[CGameState+0x310 前 6 项]  ptr=%s' % r['gsArr'])
    for s in r['gsSamples']:
        print('    [%d] idx=%s  vtable匹配CCountry=%s' % (s['i'], s['idx'], s['vtOk']))
try: frida.kill(pid)
except Exception: pass