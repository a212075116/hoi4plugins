# frida_tag_full133.py -- 输出全部 133 个国家的完整明细, 不做过滤
#
# 上一版只统计了对手数, 把"无法比对"的 79 条折叠了。这里全部展开。
# "无法比对"其实分两类, 必须区分开:
#   A. mod 权威表里根本没有这个名称   (表只覆盖 55 个名称)
#   B. 内存侧 tag 读不出 (None) 或为占位符 "---"
import frida, time, re

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
    var out = {rows: [], tags: [], nTag: 0, rawSize: 0};
    var tarr = gs.add(0x328).add(48).readPointer();
    out.rawSize = gs.add(0x328).add(60).readU32();
    for (var i = 0; i < 150; i++) {
        out.tags.push(readCString(tarr.add(i * 32)));
    }
    out.nTag = out.tags.filter(function (x) { return x !== null; }).length;
    var carr = gs.add(0x310).readPointer();
    for (var i = 0; i < 133; i++) {
        var cp;
        try { cp = carr.add(i * 8).readPointer(); } catch (e) { break; }
        if (cp.isNull()) { out.rows.push({slot: i, null: true}); continue; }
        if (!readable(cp, 0x60)) { out.rows.push({slot: i, unreadable: true}); continue; }
        var vt = cp.readPointer();
        if (!vt.equals(VT_COUNTRY)) { out.rows.push({slot: i, notCountry: true}); continue; }
        var idx = cp.add(8).readU32();
        var nm  = readCString(cp.add(0x10));
        var dfn = readCString(cp.add(0x30));
        var tag = (idx >= 0 && idx < out.tags.length) ? out.tags[idx] : null;
        out.rows.push({slot: i, idx: idx, name: nm, def: dfn, tag: tag});
    }
    return out;
};
'''

def load_yml():
    m = {}
    with open(YML, encoding='utf-8-sig') as f:
        for line in f:
            mm = re.match(r'^\s*([A-Za-z0-9_]{2,12}):\s*"(.*)"\s*$', line.strip())
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
pid = frida.spawn([EXE, '-continuelastsave', '-gdpr-compliant'])
session = frida.attach(pid)
sc = session.create_script(JS)
sc.load()
frida.resume(pid)
wait_for_map()
time.sleep(6)
r = sc.exports_sync.run()

print('[tag 数组] 声明大小=%d  实际读出有效项=%d' % (r['rawSize'], r['nTag']))
print('[mod 表] 覆盖 %d 个名称' % len(name2tag))
print('')
print('=== 全部 133 行明细 ===')
print('%-5s %-5s %-7s %-7s %-4s %s' % ('槽位', '索引', '内存tag', 'mod表', '判定', '国家名'))
print('-' * 86)
cat = {'match': [], 'mismatch': [], 'noYml': [], 'noTag': []}
for row in r['rows']:
    if row.get('null'):
        print('%-5d %-5s %-7s %-7s %-4s %s' % (row['slot'], '-', '-', '-', '空', '(槽位为空指针)'))
        continue
    if row.get('unreadable'):
        print('%-5d %-5s %-7s %-7s %-4s %s' % (row['slot'], '-', '-', '-', '?', '(指针不可读)'))
        continue
    if row.get('notCountry'):
        print('%-5d %-5s %-7s %-7s %-4s %s' % (row['slot'], '-', '-', '-', '?', '(vtable 不是 CCountry)'))
        continue
    nm = row['name']
    mt = name2tag.get(nm) if nm else None
    tg = row['tag']
    if tg is None or tg == '---':
        verdict = 'B'
        cat['noTag'].append(row)
    elif mt is None:
        verdict = 'A'
        cat['noYml'].append(row)
    elif tg == mt:
        verdict = 'OK'
        cat['match'].append(row)
    else:
        verdict = 'XX'
        cat['mismatch'].append(row)
    print('%-5d %-5d %-7s %-7s %-4s %s' % (row['slot'], row['idx'], tg, mt, verdict, nm))
print('-' * 86)
print('OK=%d  XX=%d  A(mod无此名)=%d  B(内存无tag)=%d' % (
    len(cat['match']), len(cat['mismatch']), len(cat['noYml']), len(cat['noTag'])))
print('')
print('=== A 类: mod 表里查不到名称的 (%d 个) ===' % len(cat['noYml']))
for row in cat['noYml']:
    print('    索引=%-4d 内存tag=%-6s 国家名=%-18s 定义名=%s' % (row['idx'], row['tag'], row['name'], row['def']))
print('')
print('=== B 类: 内存侧读不出 tag 的 (%d 个) ===' % len(cat['noTag']))
for row in cat['noTag']:
    print('    索引=%-4d 内存tag=%-6s 国家名=%-18s 定义名=%s' % (row['idx'], row['tag'], row['name'], row['def']))
print('')
print('=== tag 数组完整内容(前 60 项) ===')
for i in range(0, 60):
    t = r['tags'][i] if i < len(r['tags']) else None
    print('    [%3d] %s' % (i, t))
try: frida.kill(pid)
except Exception: pass