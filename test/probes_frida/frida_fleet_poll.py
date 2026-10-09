# frida_fleet_poll.py -- 轮询等待 CFleet 出现, 再全量枚举
#
# 改进点: 之前 ready() 只检查国家数, 历史还在跑(Executing History)时就抢读,
#         那时舰队还没被创建。这里改为轮询直到 totalFleets > 0 或超时。
import frida, time, os

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
OUT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/20261009_015321_原版_CGameState_CCountry_CFleet_完整枚举.txt'
SAVE = os.environ.get('FRIDA_START_SAVE', 'autosave')
ALLOWOLD = os.environ.get('FRIDA_ALLOW_OLD', '1') == '1'

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
rpc.exports.status = function () {
    try {
        var gs = GS_GLOBAL.readPointer();
        if (gs.isNull() || !readable(gs, 0x800)) return {ok: false, why: 'GS'};
        var prov = u32(gs, 0x2B0 + 8);
        var cc = u32(gs, 0x310 + 8);
        return {ok: true, provinces: prov, countries: cc};
    } catch (e) { return {ok: false, why: '' + e}; }
};
rpc.exports.fleetCount = function () {
    try {
        var gs = GS_GLOBAL.readPointer();
        var carr = gs.add(0x310).readPointer();
        var cnum = u32(gs, 0x310 + 8);
        var tot = 0;
        for (var ci = 0; ci < cnum; ci++) {
            var c;
            try { c = carr.add(ci * 8).readPointer(); } catch (e) { continue; }
            if (c.isNull() || !readable(c, 0x300)) continue;
            var n = u32(c, 0x284);
            if (n && n > 0 && n < 10000) tot += n;
        }
        return tot;
    } catch (e) { return -1; }
};
rpc.exports.run = function () {
    var gs = GS_GLOBAL.readPointer();
    var carr = gs.add(0x310).readPointer();
    var cnum = u32(gs, 0x310 + 8);
    var out = {base: base.toString(), gs: gs.toString(), provinces: u32(gs, 0x2B0 + 8),
               countries: cnum, rows: [], totalFleets: 0};
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

def dec(h):
    if h is None: return None
    try: return bytes.fromhex(h).decode('utf-8')
    except Exception: return '<非UTF8> ' + h

args = [EXE, '-gdpr-compliant', '-start_save=' + SAVE, '-nolauncher']
if ALLOWOLD: args.append('-allowoldsave')
print('[启动参数] %s' % ' '.join(args), flush=True)
pid = frida.spawn(args)
session = frida.attach(pid)
sc = session.create_script(JS)
sc.load()
print('[spawn] pid=%d' % pid, flush=True)
frida.resume(pid)

t0 = time.time()
last = None
while time.time() - t0 < 240:
    try: st = sc.exports_sync.status()
    except Exception as e: st = {'ok': False, 'why': 'rpc:%s' % e}
    if st.get('ok'):
        key = (st.get('provinces'), st.get('countries'))
        if key != last: print('  就绪中 provinces=%s countries=%s (%.0fs)' % (key[0], key[1], time.time()-t0), flush=True); last = key
        if st.get('countries', 0) > 50 and st.get('provinces', 0) > 9000: break
    else:
        if st.get('why') != last: print('  等待: %s' % st.get('why'), flush=True); last = st.get('why')
    time.sleep(1)
print('[gamestate 就绪] %.0fs' % (time.time()-t0), flush=True)

t1 = time.time()
n = 0
while time.time() - t1 < 180:
    n = sc.exports_sync.fleetCount()
    if n and n > 0:
        print('[发现舰队] %d 个  (再等 5s 让历史跑完) %.0fs' % (n, time.time()-t1), flush=True)
        time.sleep(5)
        n2 = sc.exports_sync.fleetCount()
        print('[稳定后] %d 个' % n2, flush=True)
        break
    time.sleep(2)
if not n or n <= 0: print('[超时] 仍未发现舰队', flush=True)

r = sc.exports_sync.run()

L = []
def a(s): L.append(str(s))
a('时间戳     : 20261009_015321')
a('测试模块   : 游戏根目录 hoi4.exe  (原版环境, mod 已禁用)')
a('启动参数   : %s' % ' '.join(args))
a('涉及类     : CGameState -> CCountry -> CFleet')
a('涉及函数   : CFleet::ctor  sub_140D503D0 / 创建 sub_140D545A0 / 加入 sub_140D51010')
a('             容器读取点 sub_1406D2EC0 / 名字来源 sub_140D55DC0 = qword_14332F0D8')
a('测试目的   : 全量解析 CFleet 的名字与身份(tag + ref id)')
a('完整性     : 全量输出, 不抽样, 不过滤')
a('')
a('--- 判据链 ---')
a('1. 容器  CCountry + 0x278 = CFleet* 数组, +0x284 = 元素数  (sub_1406D2EC0)')
a('2. 名字  CFleet + 0xE0 CString (size +0xF0, cap +0xF8)  (sub_140D503D0)')
a('3. 身份  CFleet + 0x08 = CReferenceObject {tag 低4字节, ref id 高4字节}')
a('4. 虚表  RVA 0x2962A18, 对象大小 0x130')
a('')
a('本次运行现场:')
a('hoi4.exe 基址 : %s' % r['base'])
a('CGameState*   : %s' % r['gs'])
a('省份数        : %s' % r['provinces'])
a('国家数        : %s' % r['countries'])
a('舰队元素总计数: %d' % r['totalFleets'])
a('')
rows = r['rows']
withF = [x for x in rows if x['fleets']]
a('有舰队槽位的国家数: %d / %d' % (len(withF), len(rows)))
a('')
a('=' * 150)
a('%-6s %-20s %-20s %-8s %s' % ('国家', 'CCountry*', 'CFleet数组*', '舰队数', '舰队明细'))
a('=' * 150)
for x in rows:
    det = []
    for f in x['fleets']:
        if f.get('null'): det.append('[%d NULL]' % f['fi']); continue
        if f.get('unreadable'): det.append('[%d 不可读 %s]' % (f['fi'], f.get('ptr'))); continue
        if f.get('err'): det.append('[%d 槽失败]' % f['fi']); continue
        det.append('[%d ptr=%s tag=%s refid=%s vt=%s name=%r |+0x48=%r |+0xB8=%r]' % (
            f['fi'], f.get('ptr'), f.get('tag'), f.get('refid'),
            ('吻合' if f.get('vtOk') else '不吻合'), dec(f.get('hex')), dec(f.get('hex48')), dec(f.get('hexB8'))))
    a('%-6d %-20s %-20s %-8s %s' % (x['ci'], x['c'], x.get('arr'), x.get('num'), ' '.join(det) if det else '(空)'))
a('')
a('--- 统计 ---')
ntot = 0; nvt = 0
names = {}
tags = {}
for x in rows:
    for f in x['fleets']:
        if f.get('ptr'):
            ntot += 1
            if f.get('vtOk'): nvt += 1
            nm = dec(f.get('hex')); names[nm] = names.get(nm, 0) + 1
            t = f.get('tag'); tags[t] = tags.get(t, 0) + 1
a('CFleet 对象数   : %d' % ntot)
a('vtable 吻合     : %d' % nvt)
a('名字去重后      : %d' % len(names))
a('出现过的 tag 数 : %d' % len(tags))
for k, v in sorted(names.items(), key=lambda kv: -kv[1])[:30]:
    a('    名字 %-40r x%d' % (k, v))
with open(OUT, 'w', encoding='utf-8') as fp: fp.write(chr(10).join(L))
print('[写出] %s  行数=%d' % (OUT, len(L)))
print('')
print('省份数 %s / 国家数 %s' % (r['provinces'], r['countries']))
print('舰队元素总计数 : %d' % r['totalFleets'])
print('CFleet 对象数  : %d' % ntot)
print('vtable 吻合    : %d' % nvt)
print('名字去重后     : %d' % len(names))
for k, v in sorted(names.items(), key=lambda kv: -kv[1])[:12]:
    print('    %-40r x%d' % (k, v))
try: frida.kill(pid)
except Exception: pass