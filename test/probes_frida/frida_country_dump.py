# frida_country_dump.py -- 定位 CCountry 实例并 dump 其结构
#
# 定位方式是可证伪的: CCountry 实例的首 8 字节必须等于 ??_7CCountry@@6B@ 的运行时地址。
# 这比猜容器偏移可靠得多。拿到实例后 dump 字段, 用其中的字符串/指针反推成员含义。
import frida, time

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
JS = '''
var base = Process.enumerateModules()[0].base;
var VT_COUNTRY = base.add(0x27E7360);

function scanWhole(pat, cap) {
    var hits = [];
    var ranges = Process.enumerateRanges('rw-');
    for (var i = 0; i < ranges.length && hits.length < cap; i++) {
        var r = ranges[i];
        if (r.size > 256 * 1024 * 1024) continue;
        var found;
        try { found = Memory.scanSync(r.base, r.size, pat); } catch (e) { continue; }
        for (var j = 0; j < found.length && hits.length < cap; j++) hits.push(found[j].address);
    }
    return hits;
}
function cstr(p, max) {
    try { return p.readUtf8String(max); } catch (e) { return null; }
}
rpc.exports.run = function () {
    var inst = scanWhole(VT_COUNTRY.toMatchPattern(), 400);
    var res = {n: inst.length, first: null};
    if (!inst.length) return res;
    var o = inst[0];
    res.first = o.toString();
    var stride = inst.length > 1 ? inst[1].sub(o).toInt32() : 0;
    res.stride = stride;
    // 前 0x200 字节逐 8 字节, 标注可疑的字符串指针
    var lines = [];
    for (var off = 0; off < 0x200; off += 8) {
        var v;
        try { v = o.add(off).readPointer(); } catch (e) { break; }
        var s = '  +0x' + ('000' + off.toString(16)).slice(-4) + ' = ' + v;
        if (!v.isNull()) {
            var t = cstr(v, 40);
            if (t && /^[\\x20-\\x7e]{1,40}$/.test(t)) s += '   "' + t + '"';
            else {
                var inExe = Process.findModuleByAddress(v);
                if (inExe && inExe.name === 'hoi4.exe') s += '   (exe+0x' + v.sub(base).toInt32().toString(16) + ')';
            }
        }
        lines.push(s);
    }
    res.lines = lines;
    return res;
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
time.sleep(3)
r = sc.exports_sync.run()
print('[CCountry 实例数] %s   步长=%s' % (r.get('n'), r.get('stride')))
print('[首个实例] %s' % r.get('first'))
for ln in r.get('lines', []): print(ln)
try: frida.kill(pid)
except Exception: pass