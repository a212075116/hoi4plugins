# frida_country_allstr.py -- 穷尽一个 CCountry 实例里的全部 CString
#
# 目的: 头部只有 3 个 CString(国家名), tag 若以字符串形式存在, 必然在更靠后的位置。
# 判据: MSVC std::string = { 16 字节数据区, size, capacity }, 且 0 <= size <= capacity。
# 这个自洽性检查足以滤掉绝大多数误判。
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
function readCString(p) {
    try {
        var size = p.add(16).readU64().toNumber();
        var cap  = p.add(24).readU64().toNumber();
        if (size === 0 || size > 300 || cap > 300 || cap < size) return null;
        if (cap !== 15 && cap !== 31 && cap !== 63 && cap < 16) return null;
        var dataP = (cap > 15) ? p.readPointer() : p;
        var s = '';
        for (var i = 0; i < size; i++) s += String.fromCharCode(dataP.add(i).readU8());
        try { return decodeURIComponent(escape(s)); } catch (e) { return s; }
    } catch (e) { return null; }
}
rpc.exports.run = function () {
    var inst = scanWhole(VT_COUNTRY.toMatchPattern(), 200);
    var out = [];
    for (var i = 0; i < inst.length; i++) {
        var o = inst[i];
        var nm = readCString(o.add(0x10));
        var strs = [];
        for (var off = 0; off + 32 <= 5904; off += 8) {
            var s = readCString(o.add(off));
            if (s !== null) strs.push({off: off, s: s});
        }
        out.push({obj: o.toString(), name: nm, strs: strs});
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
time.sleep(3)
res = sc.exports_sync.run()
print('[共 %d 个实例]' % len(res))
# 只打印名称含格黑娜 或 阿拜多斯 的, 避免刷屏
for r in res:
    if r['name'] and any(k in r['name'] for k in ('格黑娜', '阿拜多斯', '百鬼夜行')):
        print('[%s] name=%s' % (r['obj'], r['name']))
        for s in r['strs']:
            print('      +0x%04x  "%s"' % (s['off'], s['s']))
try: frida.kill(pid)
except Exception: pass