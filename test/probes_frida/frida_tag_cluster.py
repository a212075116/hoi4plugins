# frida_tag_cluster.py -- 找内存里 tag 最密集的区域, 那里就是 tag 表
#
# 已知玩家 ABY / 格黑娜 GEH / 百鬼夜行 HYA 都是裸三字母 ASCII。
# 若存在"按国家索引排列的 tag 表", 表内 tag 之间的距离应当规则。
# 做法: 收集三者的全部出现位置, 按地址排序, 找出相互距离最近的一簇, 再 dump 那一簇。
import frida, time

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
JS = '''
var base = Process.enumerateModules()[0].base;
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
rpc.exports.run = function () {
    var all = [];
    var sets = [['GEH','47 45 48'], ['HYA','48 59 41'], ['ABY','41 42 59']];
    for (var s = 0; s < sets.length; s++) {
        var h = scanWhole(sets[s][1], 300);
        for (var i = 0; i < h.length; i++) all.push({tag: sets[s][0], at: h[i]});
    }
    all.sort(function (x, y) { return x.at.compare(y.at); });
    // 找距离最近的相邻对
    var best = null;
    for (var k = 1; k < all.length; k++) {
        var d = all[k].at.sub(all[k-1].at).toInt32();
        if (d > 0 && d < 4096) {
            if (best === null || d < best.d) best = {d: d, a: all[k-1], b: all[k]};
        }
    }
    var res = {total: all.length, best: null, dump: null};
    if (best) {
        res.best = {d: best.d, aTag: best.a.tag, aAt: best.a.at.toString(), bTag: best.b.tag, bAt: best.b.at.toString()};
        // dump 这一对之前 0x100 字节的十六进制
        var start = best.a.at.sub(0x100);
        var lines = [];
        for (var row = 0; row < 0x200; row += 16) {
            var p = start.add(row);
            var hexs = '', asc = '';
            for (var c = 0; c < 16; c++) {
                var v;
                try { v = p.add(c).readU8(); } catch (e) { v = 0x3f; }
                hexs += ('0' + v.toString(16)).slice(-2) + ' ';
                asc += (v >= 0x20 && v < 0x7f) ? String.fromCharCode(v) : '.';
            }
            lines.push(p.toString() + '  ' + hexs + ' ' + asc);
        }
        res.dump = lines;
    }
    return res;
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
r = sc.exports_sync.run()
print('[tag 出现总数] %d' % r['total'])
b = r['best']
if b:
    print('[最密集相邻对] %s@%s  ->  %s@%s   距离 %d (0x%x)' % (b['aTag'], b['aAt'], b['bTag'], b['bAt'], b['d'], b['d']))
    print('[该处内存前后 0x200]')
    for ln in r['dump']: print(ln)
else:
    print('[未找到 4096 字节内的相邻对]')
try: frida.kill(pid)
except Exception: pass