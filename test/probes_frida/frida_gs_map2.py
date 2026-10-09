# frida_gs_map2.py -- 只列出 CGameState 里的指针字段, 并用虚表指纹标注
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
var gsGlobal = base.add(0x332F260);
var KNOWN = %s;
function vtName(p) {
    try {
        var nm = Process.findModuleByAddress(p);
        if (!nm || nm.name !== 'hoi4.exe') return null;
        var rva = p.sub(base).toInt32() >>> 0;
        return KNOWN[String(rva)] || ('rva:0x' + rva.toString(16));
    } catch (e) { return null; }
}
rpc.exports.dump = function () {
    var gs;
    try { gs = gsGlobal.readPointer(); } catch (e) { return {err: 'global: ' + e}; }
    if (gs.isNull()) return {err: 'null'};
    var mods = Process.enumerateModules();
    var hi = base.add(0x3800000);
    var out = ['CGameState = ' + gs + '   (exe base=' + base + ', 映像末=' + hi + ')'];
    for (var off = 0; off < 0x2000; off += 8) {
        var v;
        try { v = gs.add(off).readPointer(); } catch (e) { break; }
        if (v.isNull()) continue;
        if (v.compare(base) < 0) continue;
        var u = v.toString();
        var s = '  +0x' + ('000' + off.toString(16)).slice(-4) + ' = ' + u;
        var nm = vtName(v);
        if (nm) s += '   <== 虚表: ' + nm;
        out.push(s);
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
        except Exception:
            pass
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
r = sc.exports_sync.dump()
if 'err' in r:
    print('[!] ' + r['err'])
else:
    for ln in r['lines']:
        print(ln)
try: frida.kill(pid)
except Exception: pass