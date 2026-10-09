# frida_fleet_probe.py -- 扫堆找 CFleet 实例, 读出 tag / ref id / 名字
#
# 静态依据(全部来自反汇编):
#   虚表 RVA 0x2962A18  (??_7CFleet@@6B@, COL = ??_R4CFleet@@6B@)
#   构造函数 sub_140D503D0(this, a2):
#     *(QWORD*)this = &CFleet::vftable
#     this+0x08 = Invalid_country_tag_0        <- CReferenceObject 的引用(tag+ref id)
#     this+0x18 = &CFleet::vftable            <- 第二层虚表(多继承)
#     this+0xE0 = malloc(0x20) 名字数据指针
#     this+0xF0 = 18 (size)   this+0xF8 = 31 (capacity)
#     strcpy(名字, \"FLEET_NAME_NOT_SET\")
#   对象大小 0x130  (sub_140D545A0 里的 malloc(0x130))
#   创建点 sub_140D545A0 / sub_140705CE0(CCountry 虚表 slot 4)
#   断言: \"Added fleet has no ref id created!\"  => CReferenceObject 有 ref id
#         \"Failed to set the country when adding a fleet!\"  => CFleet 属于 CCountry
#
# 判据: 位置 p 满足
#   1. *(void**)p == hoi4.exe + 0x2962A18
#   2. p+0xE0 处构成合法 CString
import frida, time

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
JS = '''
var mods = Process.enumerateModules();
var exe = null;
for (var i = 0; i < mods.length; i++) if (mods[i].name.toLowerCase() === 'hoi4.exe') exe = mods[i];
var base = exe.base;
var GS_GLOBAL = base.add(0x332F260);
var VT_FLEET = base.add(0x2962A18);
var rs = null;
function readable(p, n) {
    if (!rs) rs = Process.enumerateRanges('r--');
    for (var i = 0; i < rs.length; i++) {
        var r = rs[i];
        if (p.compare(r.base) >= 0 && p.add(n).compare(r.base.add(r.size)) <= 0) return true;
    }
    return false;
}
function readCSHex(p) {
    try {
        var sz = Number(p.add(16).readU64());
        var cap = Number(p.add(24).readU64());
        if (sz > 400 || cap < sz || cap > 400) return null;
        if (sz === 0) return '';
        var dp = (cap > 15) ? p.readPointer() : p;
        if (!readable(dp, sz)) return null;
        var s = '';
        for (var i = 0; i < sz; i++) {
            var h = dp.add(i).readU8().toString(16);
            if (h.length === 1) h = '0' + h;
            s += h;
        }
        return s;
    } catch (e) { return null; }
}
function u32(p, off) { try { return p.add(off).readU32(); } catch (e) { return null; } }
rpc.exports.ready = function () {
    try {
        var gs = GS_GLOBAL.readPointer();
        if (gs.isNull() || !readable(gs, 0x800)) return {ok: false, why: 'GS'};
        if (gs.add(0x2B0).add(8).readU32() < 9000) return {ok: false, why: 'prov'};
        return {ok: true};
    } catch (e) { return {ok: false, why: '' + e}; }
};
rpc.exports.run = function () {
    var wr = Process.enumerateRanges('rw-');
    var pat = VT_FLEET.toMatchPattern();
    var out = {vt: VT_FLEET.toString(), raw: 0, strong: 0, rows: []};
    for (var i = 0; i < wr.length; i++) {
        var r = wr[i];
        if (r.size > 256 * 1024 * 1024) continue;
        var hits;
        try { hits = Memory.scanSync(r.base, r.size, pat); } catch (e) { continue; }
        for (var j = 0; j < hits.length; j++) {
            var a = hits[j].address;
            out.raw++;
            if (!readable(a, 0x130)) continue;
            var hex = readCSHex(a.add(0xE0));
            if (hex === null) continue;
            out.strong++;
            if (out.rows.length < 400) {
                out.rows.push({at: a.toString(), tag: u32(a, 8), refid: u32(a, 12),
                               hex: hex, q16: u32(a, 16), f18vt: (function(){ try { return a.add(0x18).readPointer().toString(); } catch(e){ return null; } })()});
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
t0 = time.time(); last = None
while time.time() - t0 < 420:
    try: st = sc.exports_sync.ready()
    except Exception as e: st = {'ok': False, 'why': 'rpc:%s' % e}
    if st.get('ok'): print('[就绪]', flush=True); break
    if st.get('why') != last: print('  等待: %s' % st.get('why'), flush=True); last = st.get('why')
    time.sleep(1)
else:
    frida.kill(pid); raise SystemExit('超时')
r = sc.exports_sync.run()
print('')
print('CFleet 虚表        : %s' % r['vt'])
print('原始命中(只比虚表) : %d' % r['raw'])
print('强判据命中(+CString): %d' % r['strong'])
print('')
rows = r['rows']
print('=== 样本(最多 40) ===')
print('%-20s %-8s %-8s %-24s %s' % ('对象', 'tag(+08)', 'refid(+0C)', '名字(+0xE0)', '+0x18虚表'))
for x in rows[:40]:
    nm = None
    try: nm = bytes.fromhex(x['hex']).decode('utf-8')
    except Exception: nm = '<非UTF8> ' + x['hex']
    print('%-20s %-8s %-8s %-24r %s' % (x['at'], x['tag'], x['refid'], nm, x['f18vt']))
print('')
names = {}
for x in rows:
    try: nm = bytes.fromhex(x['hex']).decode('utf-8')
    except Exception: nm = '<非UTF8>'
    names[nm] = names.get(nm, 0) + 1
print('名字去重后: %d' % len(names))
for k, v in sorted(names.items(), key=lambda kv: -kv[1])[:15]:
    print('    %-40r x%d' % (k, v))
try: frida.kill(pid)
except Exception: pass