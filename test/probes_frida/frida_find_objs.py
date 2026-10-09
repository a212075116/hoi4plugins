# frida_find_objs.py -- 在 CGameState 里找"指向已知类实例"的指针
#
# 不假设容器的内存布局。做法是逐个 8 字节当指针解引用, 读它指向对象的首 8 字节
# (虚表指针), 再看这个虚表是不是我们已恢复的某个类的虚表。
# 同时对"指针的指针"也做一次(容器常是 {ptr,size,cap}, ptr 指向元素数组)。
import frida, sys, time, json

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
KNOWN = {
    0x27E7360: 'CCountry', 0x2936CC0: 'CState', 0x2971B18: 'CProvince',
    0x297EA60: 'CCharacter', 0x295A2B0: 'CArmy', 0x29530D8: 'CUnit',
    0x27EB3D0: 'CDecision', 0x27D4990: 'CEffect', 0x27D55F0: 'CTrigger',
    0x2721158: 'CCurrentGameState', 0x27210E0: 'CGameState',
}
JS = '''
var base = Process.enumerateModules()[0].base;
var KNOWN = %s;
function rvaOf(p) {
    try {
        var nm = Process.findModuleByAddress(p);
        if (!nm || nm.name !== 'hoi4.exe') return -1;
        return p.sub(base).toInt32() >>> 0;
    } catch (e) { return -1; }
}
function clsOf(p) {
    var r = rvaOf(p);
    if (r < 0) return null;
    return KNOWN[String(r)] || null;
}
function isUser(p) {
    var u = p.toString();
    return p.compare(ptr('0x10000')) > 0 && u.length <= 12;
}
rpc.exports.scan = function () {
    var gs;
    try { gs = ptr('0x332F260').add(base).readPointer(); } catch (e) {
        gs = base.add(0x332F260).readPointer();
    }
    if (gs.isNull()) return {err: 'null'};
    var out = ['CGameState = ' + gs];
    for (var off = 0; off < 0x2000; off += 8) {
        var v;
        try { v = gs.add(off).readPointer(); } catch (e) { break; }
        if (v.isNull() || !isUser(v)) continue;
        var u = v.toString();
        var tag = '  +0x' + ('000' + off.toString(16)).slice(-4) + ' = ' + u;
        var direct = null, viaArr = null;
        try { direct = clsOf(v.readPointer()); } catch (e) {}
        try {
            var e0 = v.readPointer();
            if (!e0.isNull() && isUser(e0)) viaArr = clsOf(e0.readPointer());
        } catch (e) {}
        if (direct) tag += '   <== 对象: ' + direct;
        if (viaArr) tag += '   <== 数组元素: ' + viaArr;
        if (direct || viaArr) out.push(tag);
    }
    return {lines: out};
};
''' % json.dumps({str(k): v for k, v in KNOWN.items()})

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
r = sc.exports_sync.scan()
if 'err' in r: print('[!] ' + r['err'])
else:
    for ln in r['lines']: print(ln)
try: frida.kill(pid)
except Exception: pass