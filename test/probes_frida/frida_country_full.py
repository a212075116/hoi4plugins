# frida_country_full.py -- 把 133 个国家的 索引/名称 全部读出, 并对上 tag
#
# 两条路并用:
#   内存侧: CCountry+0x08 = 唯一索引, +0x10 = 国家名(CString)
#   静态侧: mod 的 localisation 给出 名称 -> tag 的权威映射
# 名称可能一对多(例如 "阿拜多斯高中" 与 "阿拜多斯"), 所以两者都打印, 便于人工判断。
import frida, time, re, os

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
YML = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/mod/bakaifa/localisation/simp_chinese/ba_countries_l_simp_chinese.yml'

# --- 静态侧: 解析 名称 -> tag ---
name2tag = {}
tag2name = {}
for line in open(YML, encoding='utf-8-sig', errors='ignore'):
    m = re.match(r'\s*([A-Za-z][A-Za-z0-9_]*)\s*:\s*"(.*)"\s*$', line)
    if not m: continue
    key, val = m.group(1), m.group(2)
    if key.endswith('_DEF') or key.endswith('_ADJ'): continue
    base = key.split('_')[0]
    tag2name.setdefault(base, val)
    if val not in name2tag: name2tag[val] = base
print('[静态侧] tag %d 个, 名称 %d 个' % (len(tag2name), len(name2tag)))

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
        var idx = null;
        try { idx = o.add(8).readU64().toNumber(); } catch (e) {}
        out.push({idx: idx, name: readCString(o.add(0x10)), def: readCString(o.add(0x30)), at: o.toString()});
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
res.sort(key=lambda r: (r['idx'] if r['idx'] is not None else 9e9))
print('[内存侧] 实例 %d 个' % len(res))
print('[索引]  [tag]  名称                  /  localisation 定义名')
hit = 0
for r in res:
    nm = r['name'] or '(空)'
    tag = name2tag.get(nm, '?')
    if tag != '?': hit += 1
    print('  %-4s   %-5s  %-16s / %s' % (r['idx'], tag, nm, r['def'] or ''))
print('[统计] 名称命中映射表: %d / %d' % (hit, len(res)))
try: frida.kill(pid)
except Exception: pass