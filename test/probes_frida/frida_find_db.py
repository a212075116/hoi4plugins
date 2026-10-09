# frida_find_db.py -- 按 IDA 字段布局定位 CCountryDatabase
#
# IDA 反编译 sub_14071BD10 (countrydatabase.cpp:89):
#   return *(_QWORD *)(db + 48) + 4LL * index;   // 元素宽 4 字节
#   范围检查用 *(_DWORD *)(db + 60)
# 且 CCountryDatabase 在 12333 个虚表里搜不到 => 非多态类, 很可能内联在 CGameState 里。
#
# 判据(可证伪): 若 CGameState+off 就是 db, 则
#   db_new = gs + off,
#   *(QWORD*)(db_new + 48) 指向一块 4 字节元素数组,
#   *(DWORD*)(db_new + 60) 是该数组的元素个数(应为 132/133 附近)。
# 同时验证: 那个数组里按 4 字节解码应能看到 tag 字符串。
import frida, time

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
JS = '''
var base = Process.enumerateModules()[0].base;
var GS_GLOBAL = base.add(0x332F260);
rpc.exports.run = function () {
    var rs = Process.enumerateRanges('r--');
    function readable(p, n) {
        for (var i = 0; i < rs.length; i++) {
            var r = rs[i];
            if (p.compare(r.base) >= 0 && p.add(n).compare(r.base.add(r.size)) <= 0) return true;
        }
        return false;
    }
    var gs = GS_GLOBAL.readPointer();
    var out = {gs: gs.toString(), cands: []};
    // 遍历 gs 前后各 0x4000, 把每个 8 字节对齐位置当作可能的 db
    for (var off = 0; off < 0x8000; off += 8) {
        var cand = gs.add(off);
        if (!readable(cand, 0x100)) continue;
        var arrPtr, arrSize;
        try {
            arrPtr = cand.add(48).readPointer();
            arrSize = cand.add(60).readU32();
        } catch (e) { continue; }
        if (arrPtr.isNull()) continue;
        if (arrSize < 100 || arrSize > 300) continue;
        if (!readable(arrPtr, arrSize * 4)) continue;
        // 该数组的前几项按 4 字节解码, 看是否像 tag
        var tags = [];
        for (var i = 0; i < Math.min(arrSize, 8); i++) {
            var b;
            try { b = new Uint8Array(arrPtr.add(i * 4).readByteArray(4)); } catch (e) { break; }
            if (b[3] === 0 && b[0] >= 65 && b[0] <= 90) {
                tags.push(String.fromCharCode(b[0], b[1], b[2]));
            } else {
                tags.push('[' + b[0] + ',' + b[1] + ',' + b[2] + ',' + b[3] + ']');
            }
        }
        out.cands.push({dbOff: off, arrPtr: arrPtr.toString(), size: arrSize, first: tags});
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
time.sleep(6)
r = sc.exports_sync.run()
print('[CGameState] %s' % r['gs'])
print('[符合 db+48/db+60 布局的候选] %d 个' % len(r['cands']))
for c in r['cands'][:20]:
    print('')
    print('    db = CGameState + 0x%x' % c['dbOff'])
    print('        +48 => %s   (size=%d)' % (c['arrPtr'], c['size']))
    print('        前几项: %s' % ' '.join(c['first']))
try: frida.kill(pid)
except Exception: pass