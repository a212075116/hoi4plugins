# frida_gs_arrays4.py -- 用 4 字节步长重扫 CGameState 的数组
#
# 之前用 8 字节步长: 于是 +724 这个 4 字节的"数组大小"被整个跳过, 什么都没找到。
# 现在依据 IDA 反编译出来的真实布局:
#   *((_QWORD*)gs + 89) = 基址   => gs + 712
#   *((_DWORD*)gs + 181) = 大小  => gs + 724
# 用 4 字节步长全扫, 并按"指针可读 + 大小合理"过滤。
import frida, time

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
JS = '''
var base = Process.enumerateModules()[0].base;
var GS_GLOBAL = base.add(0x332F260);
var SENTINEL  = base.add(0x3085170);
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
rpc.exports.run = function () {
    var gs = GS_GLOBAL.readPointer();
    var out = {gs: gs.toString(), cands: []};
    if (gs.isNull()) { out.err = 'null'; return out; }
    // 先按 IDA 给的确定偏移读
    try {
        var arrPtr = gs.add(712).readPointer();
        var arrSize = gs.add(724).readU32();
        out.ida_arr = {ptr: arrPtr.toString(), size: arrSize};
        var el0 = null, el1 = null;
        if (arrSize > 0 && arrSize < 100000 && readable(arrPtr, 8)) {
            el0 = arrPtr.readPointer();
            out.ida_el0 = el0.toString();
            if (readable(el0, 0x400)) {
                // 元素 +8 的 4 字节, 对照 CCountry+0x08 索引
                out.ida_el0_plus8 = el0.add(8).readU32();
                out.ida_el0_plus204 = el0.add(204).readU32();
            }
            el1 = arrPtr.add(8).readPointer();
            out.ida_el1 = el1.toString();
        }
    } catch (e) { out.ida_err = String(e); }
    // 再全扫 4 字节步长, 找所有像数组的字段
    if (readable(gs, 0x1000)) {
        for (var off = 0; off < 0x1000; off += 4) {
            var p2, sz2;
            try {
                p2 = gs.add(off).readPointer();
                if (p2.isNull() || p2.equals(SENTINEL)) continue;
                sz2 = gs.add(off + 8).readU32();
            } catch (e) { continue; }
            if (sz2 > 0 && sz2 <= 20000 && readable(p2, sz2 * 8)) {
                out.cands.push({off: off, ptr: p2.toString(), size: sz2});
            }
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
print('[CGameState] %s' % r['gs'])
if r.get('ida_arr'):
    print('[IDA 给出的布局] +712 ptr=%s   +724 size=%s' % (r['ida_arr']['ptr'], r['ida_arr']['size']))
    print('    el0=%s  el0+8=%s  el0+204=%s' % (r.get('ida_el0'), r.get('ida_el0_plus8'), r.get('ida_el0_plus204')))
    print('    el1=%s' % r.get('ida_el1'))
if r.get('ida_err'): print('[IDA 布局读取异常] %s' % r['ida_err'])
print('[4 字节步长扫出的候选数组] %d 个' % len(r['cands']))
for c in r['cands'][:25]:
    print('    +0x%04x  ptr=%s  size=%d' % (c['off'], c['ptr'], c['size']))
try: frida.kill(pid)
except Exception: pass