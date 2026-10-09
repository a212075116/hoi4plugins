# frida_country_tagid.py -- 列出全部国家的 (名称, +0x0008) 看该字段是不是 tag 编号
#
# 判据: 若它是 tag 的编码, 必须满足
#   (1) 133 个实例里取值两两不同(是主键)
#   (2) 与已知对照一致: 格黑娜学园=GEH 应小于 百鬼夜行联合学院=HYA (G 在 H 前)
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
        var dataP = (cap > 15) ? p.readPointer() : p;
        var s = '';
        for (var i = 0; i < size; i++) s += String.fromCharCode(dataP.add(i).readU8());
        try { return decodeURIComponent(escape(s)); } catch (e) { return s; }
    } catch (e) { return null; }
}
rpc.exports.run = function () {
    var inst = scanWhole(VT_COUNTRY.toMatchPattern(), 400);
    var out = [];
    for (var i = 0; i < inst.length; i++) {
        var o = inst[i];
        var name = readCString(o.add(0x10));
        var v8;
        try { v8 = o.add(8).readU64().toString(); } catch (e) { v8 = '?'; }
        out.push({obj: o.toString(), name: name, v8: v8});
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
print('[实例数] %d' % len(res))
vals = [r['v8'] for r in res]
uniq = len(set(vals))
print('[+0x0008 取值个数] %d   去重后 %d' % (len(vals), uniq))
print('[前 30 个 (按 +0x0008 排序)]')
rows = sorted(res, key=lambda r: int(r['v8']))
for r in rows[:30]:
    print('    %-6s  %s' % (r['v8'], r['name']))
print('    ...')
for r in rows:
    if r['name'] in ('格黑娜学园', '百鬼夜行联合学院'):
        print('    %-6s  %s   <<<' % (r['v8'], r['name']))
try: frida.kill(pid)
except Exception: pass