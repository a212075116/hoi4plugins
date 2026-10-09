import frida, time

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
OUT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/char_fields_unique.txt'

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
function readCS(p) {
    try {
        var sz = Number(p.add(16).readU64());
        var cap = Number(p.add(24).readU64());
        if (sz > 300 || cap < sz || cap > 300) return null;
        if (sz === 0) return '';
        var dp = (cap > 15) ? p.readPointer() : p;
        if (!readable(dp, sz)) return null;
        var s = '';
        for (var i = 0; i < sz; i++) s += String.fromCharCode(dp.add(i).readU8());
        return s;
    } catch (e) { return null; }
}
function u32(p, off) { try { return p.add(off).readU32(); } catch (e) { return null; } }
rpc.exports.ready = function () {
    try {
        var gs = GS_GLOBAL.readPointer();
        if (gs.isNull()) return {ok: false, why: 'GS=NULL'};
        if (!readable(gs, 0x800)) return {ok: false, why: 'GS 不可读: ' + gs};
        var sProv = gs.add(0x2B0).add(8).readU32();
        if (sProv < 9000) return {ok: false, why: 'prov=' + sProv};
        var mgr = gs.add(0x6A8).readPointer();
        if (mgr.isNull()) return {ok: false, why: 'mgr=NULL (gs=' + gs + ' prov=' + sProv + ')'};
        if (!readable(mgr, 0x40)) return {ok: false, why: 'mgr 不可读: ' + mgr};
        var sz = u32(mgr, 0x1c);
        if (!sz) return {ok: false, why: 'mgrsize=' + sz + ' mgr=' + mgr};
        return {ok: true, gs: gs.toString(), mgr: mgr.toString(), prov: sProv, mgrSize: sz};
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
    var out = {objs: objs.length, size: size, rows: [], cols: {}};
    for (var k = 0; k < objs.length; k++) {
        out.rows.push({i: k, ptr: objs[k].toString(), name: readCS(objs[k].add(0x48)), f18: u32(objs[k], 0x18)});
    }
    for (var off = 0; off < 0x130; off += 4) {
        var vals = [];
        for (var k = 0; k < objs.length; k++) vals.push(u32(objs[k], off));
        var uniq = {};
        var mn = null, mx = null;
        for (var k = 0; k < vals.length; k++) {
            uniq[vals[k]] = 1;
            if (mn === null || vals[k] < mn) mn = vals[k];
            if (mx === null || vals[k] > mx) mx = vals[k];
        }
        out.cols[off] = {uniq: Object.keys(uniq).length, min: mn, max: mx, vals: vals};
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
    if st.get('ok'): print('[就绪]', flush=True); break
    if st.get('why') != last: print('  等待: %s' % st.get('why'), flush=True); last = st.get('why')
    time.sleep(1)
else:
    frida.kill(pid); raise SystemExit('超时')
r = sc.exports_sync.run()

L = []
def a(s): L.append(str(s))
a('对象数: %d   管理器元素数: %d' % (r['objs'], r['size']))
a('')
a('=== 每个 4 字节偏移的唯一性(按唯一值数降序) ===')
a('%-10s %-10s %-22s %s' % ('偏移', '唯一值数', '范围', '判断'))
a('-' * 70)
items = sorted(r['cols'].items(), key=lambda kv: -kv[1]['uniq'])
for off, c in items:
    v = ''
    if c['uniq'] == r['objs']: v = '*** 完全唯一 ***'
    a('+0x%-7s %-10d %-22s %s' % (off, c['uniq'], '%s..%s' % (c['min'], c['max']), v))
a('')
a('=== 完全唯一的字段的完整取值(前 60 行, 与名字对照) ===')
uniqOffs = [int(off) for off, c in items if c['uniq'] == r['objs']]
a('这些偏移完全唯一: %s' % uniqOffs)
a('')
if uniqOffs:
    off0 = uniqOffs[0]
    a('以 +0x%x 为例:' % off0)
    a('%-8s %-12s %-28s %s' % ('下标', '+0x%x' % off0, '名字(+0x48)', '对照'))
    vals = r['cols'][str(off0)]['vals'] if str(off0) in r['cols'] else r['cols'][off0]['vals']
    for k in range(min(60, len(r['rows']))):
        row = r['rows'][k]
        nm = row.get('name')
        try: nm2 = nm.encode('latin-1').decode('utf-8') if nm else nm
        except Exception: nm2 = nm
        a('%-8d %-12s %-28s f18=%s' % (row['i'], vals[k], nm2, row.get('f18')))

with open(OUT, 'w', encoding='utf-8') as fp:
    fp.write(chr(10).join(L))
print('[写出] %s  行数=%d' % (OUT, len(L)))
print('')
print('完全唯一的偏移: %s' % ['+0x%x' % v for v in uniqOffs])
print('')
for off, c in items[:8]:
    print('+0x%-7s 唯一值=%-6d 范围=%s..%s' % (off, c['uniq'], c['min'], c['max']))
try: frida.kill(pid)
except Exception: pass