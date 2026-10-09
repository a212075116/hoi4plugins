# frida_fleet_enum.py -- 通过 CCountry+0x278 全量枚举 CFleet
#
# 静态依据(反汇编 sub_1406D2EC0):
#   v6 = sub_140BB4390(&tag)                    <- 用 tag 取 CCountry*
#   v8 = *(DWORD*)(v6 + 644) - 1                <- CCountry + 0x284 = 舰队数
#   loop: sub_140D597F0(*(QWORD*)(*(QWORD*)(v6 + 632) + 8*v9), ship, 1)
#                                        ^^^^^^^^^^ CCountry + 0x278 = CFleet* 数组
#   v11 = sub_140D545A0(a1 + 8)                 <- 创建 CFleet
#   sub_140D51010(v11, ship, 1)                 <- 把舰船加入舰队
#
# CFleet 字段(反汇编 sub_140D503D0):
#   +0x00 vtable (RVA 0x2962A18)   +0x08 CReferenceObject(tag + ref id)
#   +0x18 第二层 vtable            +0x48 CString
#   +0xB8 CString                  +0xE0 名字 CString (提取自 CUnitNamesDatabase)
#   对象大小 0x130
import frida, time

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
OUT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/20261009_015321_CGameState_CCountry_CFleet_完整枚举.txt'

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
        var sc = gs.add(0x310).add(8).readU32();
        if (sc < 100) return {ok: false, why: 'country size=' + sc};
        return {ok: true, countries: sc};
    } catch (e) { return {ok: false, why: '' + e}; }
};
rpc.exports.run = function () {
    var gs = GS_GLOBAL.readPointer();
    var carr = gs.add(0x310).readPointer();
    var cnum = u32(gs, 0x310 + 8);
    var out = {base: base.toString(), gs: gs.toString(), countries: cnum, rows: [], totalFleets: 0};
    for (var ci = 0; ci < cnum; ci++) {
        var c;
        try { c = carr.add(ci * 8).readPointer(); } catch (e) { continue; }
        if (c.isNull() || !readable(c, 0x300)) continue;
        var arr = null, num = null;
        try { arr = c.add(0x278).readPointer(); } catch (e) {}
        try { num = u32(c, 0x284); } catch (e) {}
        var rec = {ci: ci, c: c.toString(), arr: arr ? arr.toString() : null, num: num, fleets: []};
        if (num !== null && num > 0 && num < 10000 && arr && !arr.isNull() && readable(arr, num * 8)) {
            for (var fi = 0; fi < num; fi++) {
                var f;
                try { f = arr.add(fi * 8).readPointer(); } catch (e) { rec.fleets.push({fi: fi, err: 'slot'}); continue; }
                if (f.isNull()) { rec.fleets.push({fi: fi, null: true}); continue; }
                if (!readable(f, 0x130)) { rec.fleets.push({fi: fi, ptr: f.toString(), unreadable: true}); continue; }
                var vt = null; try { vt = f.readPointer(); } catch (e) {}
                rec.fleets.push({fi: fi, ptr: f.toString(), vtOk: (vt && vt.equals(VT_FLEET)),
                                 tag: u32(f, 8), refid: u32(f, 12),
                                 hex: readCSHex(f.add(0xE0)),
                                 hex48: readCSHex(f.add(0x48)),
                                 hexB8: readCSHex(f.add(0xB8))});
            }
            out.totalFleets += num;
        }
        out.rows.push(rec);
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

def dec(h):
    if h is None: return None
    try: return bytes.fromhex(h).decode('utf-8')
    except Exception: return '<非UTF8> ' + h

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

L = []
def a(s): L.append(str(s))
a('时间戳     : 20261009_015321')
a('测试模块   : 游戏根目录 hoi4.exe')
a('涉及类     : CGameState -> CCountry -> CFleet')
a('涉及函数   : CFleet::ctor        sub_140D503D0')
a('             CFleet 创建          sub_140D545A0')
a('             加入舰船            sub_140D51010')
a('             容器读取点          sub_1406D2EC0')
a('             名字来源单例        sub_140D55DC0 -> qword_14332F0D8 (CUnitNamesDatabase)')
a('测试目的   : 拿出 CFleet 的名字, 没有名字就证明它对应游戏中哪一个')
a('完整性     : 全量输出, 不抽样, 不过滤')
a('')
a('--- 判据链 ---')
a('1. 容器  CCountry + 0x278 = CFleet* 数组, CCountry + 0x284 = 元素数')
a('   sub_1406D2EC0 反汇编:')
a('     v6 = sub_140BB4390(&tag)                     用 tag 取 CCountry*')
a('     v8 = *(DWORD*)(v6 + 644) - 1                 CCountry + 0x284')
a('     sub_140D597F0(*(QWORD*)(*(QWORD*)(v6+632) + 8*v9), ship, 1)')
a('                                   ^^^^ CCountry + 0x278')
a('2. 名字  CFleet + 0xE0 (CString)')
a('   sub_140D503D0 反汇编: malloc(0x20) -> +0xE0, +0xF0 = 18, +0xF8 = 31')
a('   strcpy(buf, \"FLEET_NAME_NOT_SET\")')
a('   sub_140D54430 / sub_140D545A0 里由 CUnitNamesDatabase 生成后写入 +0xE0')
a('3. 身份  CFleet + 0x08 = CReferenceObject {tag(低4字节), ref id(高4字节)}')
a('   断言佐证: pFleet->IsCreated() && \"Added fleet has no ref id created!\"')
a('             pFleet->GetCountry() == this && \"Failed to set the country when adding a fleet!\"')
a('4. 虚表 RVA 0x2962A18  对象大小 0x130')
a('')
a('本次运行现场:')
a('hoi4.exe 基址 : %s' % r['base'])
a('CGameState*   : %s' % r['gs'])
a('国家数        : %s' % r['countries'])
a('舰队元素总计数: %d' % r['totalFleets'])
a('')
rows = r['rows']
tot = 0
withFleet = 0
for x in rows:
    if x['num']: tot += 1
    if x['fleets']: withFleet += 1
a('有舰队槽位的国家数: %d / %d' % (tot, len(rows)))
a('')
a('=' * 118)
a('%-6s %-20s %-20s %-8s %s' % ('国家', 'CCountry*', 'CFleet数组*', '舰队数', '舰队明细'))
a('=' * 118)
for x in rows:
    det = []
    for f in x['fleets']:
        if f.get('null'): det.append('[%d NULL]' % f['fi']); continue
        if f.get('unreadable'): det.append('[%d 不可读]' % f['fi']); continue
        if f.get('err'): det.append('[%d 槽失败]' % f['fi']); continue
        det.append('[%d tag=%s refid=%s vt=%s name=%r]' % (f['fi'], f.get('tag'), f.get('refid'),
                   ('吻合' if f.get('vtOk') else '不吻合'), dec(f.get('hex'))))
    a('%-6d %-20s %-20s %-8s %s' % (x['ci'], x['c'], x.get('arr'), x.get('num'), ' '.join(det) if det else '(空)'))
a('')

with open(OUT, 'w', encoding='utf-8') as fp:
    fp.write(chr(10).join(L))
print('[写出] %s  行数=%d' % (OUT, len(L)))
print('')
print('国家总数        : %s' % r['countries'])
print('舰队元素总计数  : %d' % r['totalFleets'])
print('有舰队槽位的国家: %d' % tot)
print('')
names = {}
nvt = 0; ntot = 0
for x in rows:
    for f in x['fleets']:
        if f.get('ptr'):
            ntot += 1
            if f.get('vtOk'): nvt += 1
            nm = dec(f.get('hex'))
            names[nm] = names.get(nm, 0) + 1
print('CFleet 对象数   : %d' % ntot)
print('vtable 吻合     : %d' % nvt)
print('名字去重后      : %d' % len(names))
for k, v in sorted(names.items(), key=lambda kv: -kv[1])[:12]:
    print('    %-36r x%d' % (k, v))
try: frida.kill(pid)
except Exception: pass