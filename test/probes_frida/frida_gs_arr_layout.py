# frida_gs_arr_layout.py -- 看 +0x2B0 / +0x2C8 这两个数组的元素到底是什么布局
#
# 背景: +0x2B0 的 size=9975 与 CProvince 实例数(9974)吻合,
#       +0x2C8 的 size=447  与 CState   实例数(446) 吻合,
#       但它们没被 vtable 指纹法认出 => 元素不是 8 字节对象指针。
# 做法: dump 元素原始字节, 看是否存在别的宽度或内联布局。
import frida, time

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
JS = '''
var base = Process.enumerateModules()[0].base;
var GS_GLOBAL = base.add(0x332F260);
var VT_PROV = base.add(0x2971b18);
var VT_STATE = base.add(0x2936cc0);
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
    } catch (e) { return 'ERR ' + e; }
}
rpc.exports.run = function () {
    var gs = GS_GLOBAL.readPointer();
    var out = {gs: gs.toString(), blocks: []};
    var offs = [0x2b0, 0x2c8];
    for (var k = 0; k < offs.length; k++) {
        var off = offs[k];
        var p = gs.add(off).readPointer();
        var sz = gs.add(off + 8).readU32();
        var rec = {off: off, ptr: p.toString(), size: sz, elems: [], probe: null};
        // 先 dump 前 256 字节原始
        rec.probe = hex(p, 256);
        // 逐 8 字节取指针并尝试作为对象
        for (var i = 0; i < 6; i++) {
            var e = null;
            try { e = p.add(i * 8).readPointer(); } catch (err) {}
            var item = {i: i, raw: hex(p.add(i * 8), 8)};
            if (e && !e.isNull() && readable(e, 16)) {
                item.ptr = e.toString();
                try {
                    var vt = e.readPointer();
                    var rva = vt.sub(base);
                    item.vtRva = '0x' + rva.toString(16);
                    item.isProv = vt.equals(VT_PROV);
                    item.isState = vt.equals(VT_STATE);
                } catch (err) {}
                // 若它指向的对象内部又有 vtable, 试第二层
                try {
                    var inner = e.readPointer();
                    var irva = inner.sub(base);
                    item.innerVtRva = '0x' + irva.toString(16);
                } catch (err) {}
            }
            rec.elems.push(item);
        }
        out.blocks.push(rec);
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
print('[CGameState] %s' % r['gs'])
for b in r['blocks']:
    print('')
    print('=== +0x%x  ptr=%s  size=%d ===' % (b['off'], b['ptr'], b['size']))
    print('  [前 256 字节]')
    h = b['probe'].split(' ')
    for i in range(0, min(len(h), 256), 16):
        print('    %s' % ' '.join(h[i:i+16]))
    print('  [前 6 个 8 字节槽]')
    for e in b['elems']:
        print('    [%d] raw=%s  ptr=%s  vtRva=%s  isProv=%s isState=%s' % (
            e['i'], e['raw'], e.get('ptr'), e.get('vtRva'), e.get('isProv'), e.get('isState')))
try: frida.kill(pid)
except Exception: pass