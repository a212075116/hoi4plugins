# frida_find_tagarray.py -- 定位 CCountryDatabase 的 tag 数组
#
# 依据 IDA 反编译 sub_14071BD10 (countrydatabase.cpp:89):
#   return *(_QWORD *)(db + 48) + 4LL * index;   // 元素宽 4 字节
#   大小在 *(DWORD*)(db + 60)
# 且断言 OutCountries[i]->GetCountryTag().GetIndex() == i 说明下标即国家索引。
#
# 判据(可证伪): 真正的 tag 数组是 133 个连续的 4 字节 tag,
#   所以同一块 532 字节里应能同时看到 ABY/GEH/HYA 等多个已知 tag。
#   若某个 ABY+00 附近 532 字节内没有其它已知 tag, 那它就不是数组成员。
import frida, time

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
JS = '''
var base = Process.enumerateModules()[0].base;
// 已确认的真实 tag (来自 mod 局部化表 / 内存对照)
var KNOWN = ['ABY','ABD','ARH','ARI','CA1','CAB','CAE','CAH','CAO','CAP','CEN','GEH','HIL','HYA','KRO','MIL','ODY','RWT','SCH','SHA','SRT','TRY','VAL','WLH','WS1','WS2','WS3','WV1','AB1','AR1','GE1','HI1','HS1','HY1','KR1','MI1','OD1','PMC','RW1','SH1','SR1','ST1','TR1','VA1','WL1','FJW','FJ1','PSR','AMR','W00'];
function pat4(s) {
    var out = [];
    for (var i = 0; i < 3; i++) out.push(('0' + s.charCodeAt(i).toString(16)).slice(-2));
    out.push('00');
    return out.join(' ');
}
rpc.exports.run = function () {
    var rs = Process.enumerateRanges('rw-');
    var hits = [];
    // 先找所有 ABY+00
    for (var i = 0; i < rs.length && hits.length < 3000; i++) {
        var r = rs[i];
        if (r.size > 128 * 1024 * 1024) continue;
        var res;
        try { res = Memory.scanSync(r.base, r.size, pat4('ABY')); } catch (e) { continue; }
        for (var j = 0; j < res.length && hits.length < 3000; j++) hits.push(res[j].address);
    }
    var out = {nAby: hits.length, clusters: []};
    // 对每个 ABY, 统计它前后 532 字节内出现了多少个已知 tag
    for (var k = 0; k < hits.length; k++) {
        var a = hits[k];
        var start = a.sub(532 * 4 / 2);
        var buf;
        try { buf = start.readByteArray(532 * 4); } catch (e) { continue; }
        var u8 = new Uint8Array(buf);
        var cnt = 0;
        var names = [];
        for (var n = 0; n < KNOWN.length; n++) {
            var t = KNOWN[n];
            var c0 = t.charCodeAt(0), c1 = t.charCodeAt(1), c2 = t.charCodeAt(2);
            for (var off = 0; off + 4 <= u8.length; off += 4) {
                if (u8[off] === c0 && u8[off+1] === c1 && u8[off+2] === c2 && u8[off+3] === 0) {
                    cnt++; names.push(t);
                    break;
                }
            }
        }
        if (cnt >= 5) {
            out.clusters.push({addr: a.toString(), cnt: cnt, tags: names.slice(0, 20), start: start.toString()});
        }
    }
    // 按命中数排序
    out.clusters.sort(function (x, y) { return y.cnt - x.cnt; });
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
time.sleep(6)
r = sc.exports_sync.run()
print('[ABY 命中总数] %d' % r['nAby'])
print('[疑似 tag 数组的簇(532 字节内命中 >=5 个已知 tag)] %d 个' % len(r['clusters']))
for c in r['clusters'][:12]:
    print('    基址=%s  命中=%d' % (c['addr'], c['cnt']))
    print('        tags: %s' % ', '.join(c['tags']))
try: frida.kill(pid)
except Exception: pass