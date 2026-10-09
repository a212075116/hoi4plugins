# frida_find_container.py -- 从引用 CCountry 首实例的地址里挑出容器
#
# 容器判据不是"像不像指针", 而是可证伪的事实: 一个 CPdxArray 形如
#   { ptr, size, capacity },  ptr 指向元素数组, 且 size 应当等于我们数出来的实例数。
# 所以直接读每个候选位置的 +8/+16, 看 size 是否 == 133(实例数)。
import frida, time

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
JS = '''
var base = Process.enumerateModules()[0].base;
var VT_COUNTRY = base.add(0x27E7360);
var GS_GLOBAL = base.add(0x332F260);

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

rpc.exports.run = function () {
    var res = {};
    var inst = scanWhole(VT_COUNTRY.toMatchPattern(), 400);
    res.n = inst.length;
    var gs = base.add(0x332F260).readPointer();
    res.gs = gs.toString();
    if (inst.length === 0) return res;
    var first = inst[0];
    res.first = first.toString();
    res.stride = inst.length > 1 ? inst[1].sub(first).toInt32() : -1;
    // 回搜引用
    var refs = scanWhole(first.toMatchPattern(), 300);
    var cands = [];
    for (var k = 0; k < refs.length; k++) {
        var a = refs[k];
        var size = null, cap = null, p = null;
        try {
            size = a.add(8).readU64().toString();
            cap  = a.add(16).readU64().toString();
            p    = a.readPointer().toString();
        } catch (e) { continue; }
        cands.push({at: a.toString(), ptr: p, size: size, cap: cap});
    }
    res.cands = cands;
    // 容器里第一个元素是否就是 CCountry 首实例
    res.gsDelta = gs.isNull() ? null : first.sub(gs).toInt32();
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
print('[CGameState] %s' % r.get('gs'))
print('[CCountry 实例数] %s   步长=%s   首实例=%s' % (r.get('n'), r.get('stride'), r.get('first')))
print('[首实例 与 CGameState 的差值] %s' % r.get('gsDelta'))
print('[候选容器]')
n = r.get('n')
for c in r.get('cands', []):
    mark = ''
    if c['size'] == str(n): mark += '   <<<< size 恰等于实例数!'
    print('    at %s  ptr=%s size=%s cap=%s%s' % (c['at'], c['ptr'], c['size'], c['cap'], mark))
try: frida.kill(pid)
except Exception: pass