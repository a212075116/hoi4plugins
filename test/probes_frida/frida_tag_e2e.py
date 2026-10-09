# frida_tag_e2e.py -- 端到端验证: 用静态路径读出 tag, 再与 mod 权威表逐条比对
#
# 取值路径(全部来自 IDA 静态分析 + 前面的动态验证):
#   qword_14332F260          -> CGameState*        (静态锚点, RVA 0x332F260)
#   CGameState + 0x310       -> CCountry* 数组     (133 项, vtable 指纹已验证)
#   CCountry + 0x08          -> 唯一索引
#   CGameState + 0x328 + 48  -> tag 数组           (133 项 CString, 首项 "---")
#
# 验收判据(可证伪): 对每个国家, 用索引去 tag 数组取出的 tag,
#   必须与 mod localisation 里该名字对应的 tag 完全一致。
#   任何一条不一致都算失败。
import frida, time, re, os, sys

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
YML = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa/localisation/simp_chinese/ba_countries_l_simp_chinese.yml'

JS = '''
var base = Process.enumerateModules()[0].base;
var GS_GLOBAL = base.add(0x332F260);
var VT_COUNTRY = base.add(0x27E7360);
var rs = null;
function readable(p, n) {
    if (!rs) rs = Process.enumerateRanges('r--');
    for (var i = 0; i < rs.length; i++) {
        var r = rs[i];
        if (p.compare(r.base) >= 0 && p.add(n).compare(r.base.add(r.size)) <= 0) return true;
    }
    return false;
}
function readCString(p) {
    try {
        var size = Number(p.add(16).readU64());
        var cap  = Number(p.add(24).readU64());
        if (size === 0 || size > 300 || cap > 300 || cap < size) return null;
        var dp = (cap > 15) ? p.readPointer() : p;
        var s = '';
        for (var i = 0; i < size; i++) s += String.fromCharCode(dp.add(i).readU8());
        try { return decodeURIComponent(escape(s)); } catch (e) { return s; }
    } catch (e) { return null; }
}
rpc.exports.run = function () {
    var gs = GS_GLOBAL.readPointer();
    var out = {gs: gs.toString(), rows: [], tagArr: null, nTag: 0};
    // tag 数组: CGameState + 0x328 + 48
    var db = gs.add(0x328);
    var tarr = db.add(48).readPointer();
    out.tagArr = tarr.toString();
    // 项宽 32 字节 (CString), 首项应为 "---"
    var tags = [];
    for (var i = 0; i < 140; i++) {
        var e = tarr.add(i * 32);
        var s = readCString(e);
        tags.push(s);
    }
    out.nTag = tags.filter(function (x) { return x !== null; }).length;
    out.tags = tags;
    // 国家数组: CGameState + 0x310
    var carr = gs.add(0x310).readPointer();
    out.carr = carr.toString();
    for (var i = 0; i < 133; i++) {
        var cp;
        try { cp = carr.add(i * 8).readPointer(); } catch (e) { break; }
        if (cp.isNull()) continue;
        if (!readable(cp, 0x60)) continue;
        var vt = cp.readPointer();
        if (!vt.equals(VT_COUNTRY)) continue;
        var idx = cp.add(8).readU32();
        var nm = readCString(cp.add(0x10));
        // 用索引去 tag 数组取 tag。
        // 上一轮曾写成 tags[idx-1] 导致端到端比对全错, 失败明细显示系统性偏移一位;
        // 修正为 tags[idx]: 数组下标与 CCountry+0x08 一一相等(tags[0] 是 "---" 无效占位)。
        var tag = (idx >= 0 && idx < tags.length) ? tags[idx] : null;
        out.rows.push({i: i, idx: idx, name: nm, tag: tag});
    }
    return out;
};
'''

def load_yml():
    m = {}
    with open(YML, encoding='utf-8-sig') as f:
        for line in f:
            mm = re.match(r'^\s*([A-Za-z0-9_]{2,10}):\s*"(.*)"\s*$', line.strip())
            if not mm: continue
            k, v = mm.group(1), mm.group(2)
            if k.endswith('_DEF') or k.endswith('_ADJ'): continue
            m.setdefault(v, k)
    return m

def wait_for_map(timeout=300):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            if 'Launching SINGLEPLAYER-game' in open(GAMELOG, encoding='utf-8', errors='ignore').read():
                return True
        except Exception: pass
        time.sleep(0.4)
    return False

name2tag = load_yml()
print('[mod 表] %d 个名称->tag 映射' % len(name2tag))

pid = frida.spawn([EXE, '-continuelastsave', '-gdpr-compliant'])
session = frida.attach(pid)
sc = session.create_script(JS)
sc.load()
print('[spawn] pid=%d' % pid, flush=True)
frida.resume(pid)
print('[map] = %s' % wait_for_map(), flush=True)
time.sleep(6)
r = sc.exports_sync.run()
print('')
print('=== 静态取值路径 ===')
print('CGameState           = %s' % r['gs'])
print('CCountry 数组 (+0x310) = %s' % r['carr'])
print('tag 数组 (+0x328+48)   = %s   有效项=%d' % (r['tagArr'], r['nTag']))
print('tag 数组前 5 项: %s' % r['tags'][:5])
print('')
print('=== 逐条比对 (内存读出的 tag  vs  mod 表) ===')
ok = bad = none = 0
badlist = []
for row in r['rows']:
    nm = row['name']
    mt = name2tag.get(nm) if nm else None
    if row['tag'] is None or row['tag'] == '---':
        none += 1
        continue
    if mt is None:
        none += 1
        continue
    if row['tag'] == mt:
        ok += 1
    else:
        bad += 1
        badlist.append((row['idx'], nm, row['tag'], mt))
print('    一致: %d    不一致: %d    无法比对: %d' % (ok, bad, none))
if badlist:
    print('')
    print('    [不一致明细]')
    for idx, nm, a, b in badlist[:25]:
        print('        idx=%-4d %-16s 内存=%s  mod表=%s' % (idx, nm, a, b))
print('')
print('    [前 20 条明细]')
for row in r['rows'][:20]:
    mt = name2tag.get(row['name']) if row['name'] else None
    mark = 'OK' if (row['tag'] and mt and row['tag'] == mt) else ('--' if row['tag'] in (None, '---') else 'XX')
    print('        %s  idx=%-4s 内存tag=%-6s mod表=%-6s  %s' % (mark, row['idx'], row['tag'], mt, row['name']))
print('')
print('结论: %s' % ('通过' if bad == 0 and ok > 20 else '未通过'))
try: frida.kill(pid)
except Exception: pass