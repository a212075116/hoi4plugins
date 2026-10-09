# frida_tag_table.py -- 定位"索引 -> tag"表
#
# 已知: CCountry+0x08 是 0..132 的唯一索引; 格黑娜学园=GEH(索引17), 百鬼夜行=HYA(索引20)。
# 若存在 tag 表, 那么以某个步长 s 排列时, 表内第 17 项应是 GEH, 第 20 项应是 HYA。
# 做法: 在同时含 GEH 和 HYA 的内存区域里, 测出它们之间的距离, 反推步长与表基址。
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
    var geh = scanWhole('47 45 48', 200);
    var hya = scanWhole('48 59 41', 200);
    var aby = scanWhole('41 42 59', 200);
    // 找出"同一块内存里既有 GEH 又有 HYA"的配对, 距离最近的那对最可能是同一张表
    var best = null;
    for (var i = 0; i < geh.length; i++) {
        for (var j = 0; j < hya.length; j++) {
            var d = hya[j].sub(geh[i]).toInt32();
            if (d > 0 && d < 100000) {
                if (best === null || d < best.d) best = {d: d, g: geh[i].toString(), h: hya[j].toString()};
            }
        }
    }
    return {nGeh: geh.length, nHya: hya.length, nAby: aby.length, best: best,
            geh: geh.slice(0,10).map(function(a){return a.toString();}),
            hya: hya.slice(0,10).map(function(a){return a.toString();})};
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
print('[GEH 出现] %d   [HYA 出现] %d   [ABY 出现] %d' % (r['nGeh'], r['nHya'], r['nAby']))
print('[GEH 位置样本]')
for a in r['geh']: print('    ' + a)
print('[HYA 位置样本]')
for a in r['hya']: print('    ' + a)
b = r['best']
if b:
    print('[最近的 GEH/HYA 配对] GEH %s -> HYA %s   距离 %d (0x%x)' % (b['g'], b['h'], b['d'], b['d']))
    print('   索引差 = 20-17 = 3, 若同表则步长 = %d/3 = %.1f' % (b['d'], b['d']/3.0))
else:
    print('[未找到配对]')
try: frida.kill(pid)
except Exception: pass