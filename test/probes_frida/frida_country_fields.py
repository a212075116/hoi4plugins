# frida_country_fields.py -- 在国家对象里找 '数组' 字段(指针 + 数量)
#
# 背景: CCountry + 0x278 实测全是 0。可能是偏移不对, 也可能这个存档真的没有舰队。
# 做法: 遍历 133 个 CCountry, 对每个 8 字节偏移统计:
#   - 有多少个国家在该偏移处有一个 '可读的堆指针'
#   - 该偏移 +8 处的 DWORD 是否是一个合理的小数量
# 这样能直接看出哪个偏移真的是数组。
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
        var sc = gs.add(0x310).add(8).readU32();
        if (sc < 100) return {ok: false, why: 'countries=' + sc};
        return {ok: true, countries: sc};
    } catch (e) { return {ok: false, why: '' + e}; }
};
rpc.exports.run = function () {
    var gs = GS_GLOBAL.readPointer();
    var carr = gs.add(0x310).readPointer();
    var cnum = u32(gs, 0x310 + 8);
    var cs = [];
    for (var i = 0; i < cnum; i++) {
        var c;
        try { c = carr.add(i * 8).readPointer(); } catch (e) { continue; }
        if (c.isNull() || !readable(c, 0x700)) continue;
        cs.push(c);
    }
    var out = {countries: cs.length, cols: {}};
    for (var off = 0; off < 0x700; off += 8) {
        var nonNull = 0, ptrLike = 0, sizes = [], sampleP = null, sampleC = null;
        for (var k = 0; k < cs.length; k++) {
            var v = null;
            try { v = cs[k].add(off).readPointer(); } catch (e) { continue; }
            if (v.isNull()) continue;
            nonNull++;
            // 堆上指针(高位是 0x1xx 或 0x2xx 之类), 且指向可读内存
            var hi = v.toString();
            if (readable(v, 8)) {
                ptrLike++;
                var sz = u32(cs[k], off + 8);
                if (sz !== null && sz < 100000) sizes.push(sz);
                if (sampleP === null) { sampleP = hi; sampleC = cs[k].toString(); }
            }
        }
        if (ptrLike > 0) {
            var mx = sizes.length ? Math.max.apply(null, sizes) : -1;
            var sum = sizes.reduce(function(a2,b){return a2+b;}, 0);
            out.cols[off] = {nonNull: nonNull, ptrLike: ptrLike, n: cs.length,
                             maxSize: mx, sumSize: sum, sampleP: sampleP, sampleC: sampleC};
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
t0 = time.time(); last = None
while time.time() - t0 < 420:
    try: st = sc.exports_sync.ready()
    except Exception as e: st = {'ok': False, 'why': 'rpc:%s' % e}
    if st.get('ok'): print('[就绪] %s' % st, flush=True); break
    if st.get('why') != last: print('  等待: %s' % st.get('why'), flush=True); last = st.get('why')
    time.sleep(1)
else:
    frida.kill(pid); raise SystemExit('超时')
r = sc.exports_sync.run()
print('国家数:', r['countries'])
print('')
print('%-10s %-8s %-10s %-10s %-10s %s' % ('偏移', '非空数', '可读指针数', 'size最大', 'size总和', '样本'))
print('-' * 96)
items = sorted(r['cols'].items(), key=lambda kv: int(kv[0]))
for off, c in items:
    print('+0x%-7x %-8d %-10d %-10d %-10d ptr=%s' % (int(off), c['nonNull'], c['ptrLike'], c['maxSize'], c['sumSize'], c['sampleP']))
try: frida.kill(pid)
except Exception: pass