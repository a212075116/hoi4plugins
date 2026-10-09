# frida_gs_containers.py -- 重新扫 CCurrentGameState 的容器(这次游戏已真正载入地图)
#
# 之前判定"CGameState 的容器是空的"是进入地图瞬间的读数, 不能代表稳定状态。
# 现在按 CPdxArray 的真实形状 {ptr, size, cap} 扫描, 并把空哨兵排除掉。
# 空哨兵 = hoi4.exe + 0x3085170 (静态符号 off_143085170), 这是上一轮实测确定的。
import frida, time

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
JS = '''
var base = Process.enumerateModules()[0].base;
var GS_GLOBAL = base.add(0x332F260);   // CCurrentGameState*
var SENTINEL  = base.add(0x3085170);   // 空容器哨兵
function fmt(p) { try { return p.toString(); } catch (e) { return '?'; } }
rpc.exports.run = function () {
    var gs = GS_GLOBAL.readPointer();
    var out = {gs: gs.toString(), sentinel: SENTINEL.toString(), fields: []};
    if (gs.isNull()) { out.err = 'CGameState is NULL'; return out; }
    for (var off = 0; off < 0x800; off += 8) {
        var p, sz, cap;
        try {
            p = gs.add(off).readPointer();
            sz = gs.add(off + 8).readU64().toNumber();
            cap = gs.add(off + 16).readU64().toNumber();
        } catch (e) { break; }
        var isEmpty = (p.equals(SENTINEL));
        var isNull = p.isNull();
        if (isEmpty || isNull) { out.fields.push({off: off, kind: isEmpty ? 'sentinel' : 'null'}); continue; }
        // 只看像容器头的: 有合理 size/cap
        if (sz > 0 && sz <= 100000 && cap >= sz && cap <= 200000) {
            var sample = '';
            try { sample = p.readUtf8String(28); } catch (e) { sample = null; }
            out.fields.push({off: off, kind: 'array', ptr: fmt(p), size: sz, cap: cap, sample: sample});
        }
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
print('[CCurrentGameState] %s' % r['gs'])
print('[空容器哨兵] %s' % r['sentinel'])
nS = sum(1 for f in r['fields'] if f['kind'] == 'sentinel')
nN = sum(1 for f in r['fields'] if f['kind'] == 'null')
nA = sum(1 for f in r['fields'] if f['kind'] == 'array')
print('[统计] 哨兵 %d   空指针 %d   疑似数组 %d' % (nS, nN, nA))
print('[疑似数组]')
for f in r['fields']:
    if f['kind'] == 'array':
        s = f['sample'].replace(chr(10),' ')[:24] if f['sample'] else ''
        print('    +0x%04x  ptr=%s  size=%-6d cap=%-6d  %s' % (f['off'], f['ptr'], f['size'], f['cap'], s))
try: frida.kill(pid)
except Exception: pass