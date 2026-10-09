# frida_char_fields.py -- 扫 CCharacter 对象每个 4 字节偏移的唯一性, 找唯一 id 字段
# 对象大小 0x130, 全量 2451 个, 统计每个偏移上取值的去重数量。
import frida, time

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'

JS = '''
var mods = Process.enumerateModules();
var exe = null;
for (var i = 0; i < mods.length; i++) if (mods[i].name.toLowerCase() === 'hoi4.exe') exe = mods[i];
var base = exe.base;
var GS_GLOBAL = base.add(0x332F260);
var rs = null;
function readable(p, n) {
    if (!rs) rs = Process.enumerateRanges('r--');
    for (var i = 0; i < rs.length; i++) {
        var r = rs[i];
        if (p.compare(r.base) >= 0 && p.add(n).compare(r.base.add(r.size)) <= 0) return true;
    }
    return false;
}
function u32(p, off) { try { return p.add(off).readU32(); } catch (e) { return null; } }
rpc.exports.ready = function () {
    try {
        var gs = GS_GLOBAL.readPointer();
        if (gs.isNull() || !readable(gs, 0x800)) return {ok: false, why: 'GS'};
        var sProv = gs.add(0x2B0).add(8).readU32();
        if (sProv < 9000) return {ok: false, why: 'prov=' + sProv};
        var mgr = gs.add(0x6A8).readPointer();
        if (mgr.isNull() || !readable(mgr, 0x40)) return {ok: false, why: 'mgr'};
        var sz = u32(mgr, 0x1c);
        if (!sz) return {ok: false, why: 'mgrsize'};
        return {ok: true, mgrSize: sz};
    } catch (e) { return {ok: false, why: '' + e}; }
};
rpc.exports.run = function () {
    var gs = GS_GLOBAL.readPointer();
    var mgr = gs.add(0x6A8).readPointer();
    var arr = mgr.add(0x10).readPointer();
    var size = u32(mgr, 0x1c);
    var objs = [];
    for (var i = 0; i < size; i++) {
        var p;
        try { p = arr.add(i * 8).readPointer(); } catch (e) { continue; }
        if (p.isNull() || !readable(p, 0x130)) continue;
        objs.push(p);
    }
    // 对每个 4 字节偏移, 收集全部取值
    var cols = {};
    for (var off = 0; off < 0x130; off += 4) {
        var vals = [];
        for (var k = 0; k < objs.length; k++) {
            var v = u32(objs[k], off);
            if (v !== null) vals.push(v);
        }
        cols[off] = vals;
    }
    var out = {objs: objs.length, size: size, cols: {}};
    for (var off in cols) {
        var vals = cols[off];
        var uniq = {};
        var nz = 0;
        var min = null, max = null;
        for (var k = 0; k < vals.length; k++) {
            uniq[vals[k]] = 1;
            if (vals[k] !== 0) nz++;
            if (min === null || vals[k] < min) min = vals[k];
            if (max === null || vals[k] > max) max = vals[k];
        }
        out.cols[off] = {uniq: Object.keys(uniq).length, nonZero: nz, n: vals.length, min: min, max: max};
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
t0 = time.time(); last = None
while time.time() - t0 < 300:
    try: st = sc.exports_sync.ready()
    except Exception as e: st = {'ok': False, 'why': 'rpc:%s' % e}
    if st.get('ok'): print('[就绪] %s' % st, flush=True); break
    if st.get('why') != last: print('  等待: %s' % st.get('why'), flush=True); last = st.get('why')
    time.sleep(1)
else:
    frida.kill(pid); raise SystemExit('超时')
r = sc.exports_sync.run()
print('')
print('对象数=%d   管理器元素数=%d' % (r['objs'], r['size']))
print('')
print('%-8s %-12s %-10s %-14s %s' % ('偏移', '唯一值数', '非零数', '范围', '判断'))
print('-' * 78)
items = sorted(r['cols'].items(), key=lambda kv: -kv[1]['uniq'])
for off, c in items:
    verdict = ''
    if c['uniq'] == r['objs']: verdict = '*** 完全唯一 ***'
    elif c['uniq'] > r['objs'] * 0.9: verdict = '接近唯一'
    print('+0x%-5s %-12d %-10d %-14s %s' % (off, c['uniq'], c['nonZero'], '%s..%s' % (c['min'], c['max']), verdict))
try: frida.kill(pid)
except Exception: pass