# frida_scan_diag.py -- 诊断 Memory.scanSync 在当前进程里到底能不能找到已知值
#
# 背景: 同一进程里, 上一轮用 toMatchPattern 扫到 3749 个 CCharacter 虚表值,
# 这一轮同样代码却是 0, 且可写段数从 8823 变成 2600。怀疑扫描方式/范围有问题。
#
# 本脚本用三个已知值做自检:
#   CProvince 虚表 RVA 0x2971B18  (上一轮确认 9974 个对象都在引用它)
#   CState    虚表 RVA 0x2936CC0  (446 个)
#   CCharacter虚表 RVA 0x297EA60
# 用两种方式扫: enumerateRanges('rw-') 与 enumerateRanges('r--'), 以及逐段统计。
import frida, time

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
JS = '''
var mods = Process.enumerateModules();
var exe = null;
for (var i = 0; i < mods.length; i++) if (mods[i].name.toLowerCase() === 'hoi4.exe') exe = mods[i];
var base = exe.base;
var TARGETS = [
    {name: 'CProvince', vt: base.add(0x2971B18)},   // 已知有 9974 个对象
    {name: 'CState',    vt: base.add(0x2936CC0)},   // 已知有 446 个
    {name: 'CCharacter',vt: base.add(0x297EA60)}
];
rpc.exports.run = function (prot) {
    var rs = Process.enumerateRanges(prot);
    var out = {prot: prot, ranges: rs.length, totalBytes: 0, results: []};
    for (var i = 0; i < rs.length; i++) out.totalBytes += rs[i].size;
    for (var t = 0; t < TARGETS.length; t++) {
        var pat = TARGETS[t].vt.toMatchPattern();
        var cnt = 0; var first = null;
        for (var i = 0; i < rs.length; i++) {
            var r = rs[i];
            var hits;
            try { hits = Memory.scanSync(r.base, r.size, pat); } catch (e) { continue; }
            cnt += hits.length;
            if (hits.length > 0 && first === null) first = {at: hits[0].address.toString(), seg: r.base.toString(), sz: r.size};
        }
        out.results.push({name: TARGETS[t].name, vt: TARGETS[t].vt.toString(), count: cnt, first: first});
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
time.sleep(8)
for prot in ('rw-', 'r--', 'r--'):
    r = sc.exports_sync.run(prot)
    print('')
    print('=== protection=%s  段数=%d  总字节=%d ===' % (r['prot'], r['ranges'], r['totalBytes']))
    for x in r['results']:
        print('    %-12s vt=%s  命中=%d  首个=%s' % (x['name'], x['vt'], x['count'], x['first']))
try: frida.kill(pid)
except Exception: pass