# frida_dump_tagarray.py -- dump 已定位的 tag 数组, 确认它的起止与项宽
#
# 上一轮: 在 0x211ed9ffbd0 附近, 2128 字节窗口里按索引顺序命中 29 个已知 tag。
#   顺序为 ABY, ABD, ARH, ARI, CA1, CAB, ... => 这不可能来自字符串池。
# 本轮: 向前后各 dump 2048 字节, 找出数组真正的起点, 并按 4 字节逐项解码。
import frida, time, re

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
JS = '''
var base = Process.enumerateModules()[0].base;
rpc.exports.run = function () {
    // 重新定位: 找 ABY+00 且附近含 GEH+00 与 HYA+00 的位置
    var rs = Process.enumerateRanges('rw-');
    var hits = [];
    for (var i = 0; i < rs.length && hits.length < 3000; i++) {
        var r = rs[i];
        if (r.size > 128 * 1024 * 1024) continue;
        var res;
        try { res = Memory.scanSync(r.base, r.size, '41 42 59 00'); } catch (e) { continue; }
        for (var j = 0; j < res.length && hits.length < 3000; j++) hits.push(res[j].address);
    }
    var best = null;
    for (var k = 0; k < hits.length; k++) {
        var a = hits[k];
        var start = a.sub(2048);
        var buf;
        try { buf = start.readByteArray(4096); } catch (e) { continue; }
        var u8 = new Uint8Array(buf);
        var cnt = 0;
        var known = ['ABD','ARH','ARI','CA1','GEH','HYA','KRO','MIL','SRT','TRY','VAL','PSR'];
        for (var n = 0; n < known.length; n++) {
            var t = known[n];
            for (var off = 0; off + 4 <= u8.length; off += 4) {
                if (u8[off] === t.charCodeAt(0) && u8[off+1] === t.charCodeAt(1) && u8[off+2] === t.charCodeAt(2) && u8[off+3] === 0) { cnt++; break; }
            }
        }
        if (!best || cnt > best.cnt) best = {addr: a.toString(), cnt: cnt, start: start.toString()};
    }
    if (!best) return {err: 'not found'};
    var r2 = {addr: best.addr, cnt: best.cnt, start: best.start, bytes: null};
    var buf2;
    try {
        buf2 = ptr(best.start).readByteArray(4096);
    } catch (e) { return {err: 'read fail ' + e}; }
    var u = new Uint8Array(buf2);
    var hex = [];
    for (var i = 0; i < u.length; i++) hex.push(('0' + u[i].toString(16)).slice(-2));
    r2.bytes = hex.join('');
    return r2;
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
    print('[最佳簇] ABY@%s  命中=%d  窗口起点=%s' % (r['addr'], r['cnt'], r['start']))
    b = bytes.fromhex(r['bytes'])
    print('')
    print('[按 4 字节逐项解码, 从窗口起点开始]')
    for i in range(0, len(b) - 3, 4):
        v = b[i:i+4]
        if v[3] != 0: continue
        try:
            s = v[:3].decode('ascii')
        except Exception:
            continue
        if re.fullmatch(r'[A-Z0-9]{3}', s):
            print('    +0x%04x  [idx %3d]  %s' % (i, i // 4, s))
try: frida.kill(pid)
except Exception: pass