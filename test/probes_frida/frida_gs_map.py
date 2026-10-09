# frida_gs_map.py -- 地图加载后 dump CGameState, 并用虚表指纹标注每个指针字段
#
# 为什么不用插件: 插件要重编译-重启游戏, 而这里可以边看边改。
# 判据仍然不是时间: 等游戏日志出现 Launching SINGLEPLAYER-game 才开始看。
import frida, sys, time, json, os

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
GS_GLOBAL = 0x332F260

# 已知类的虚表 RVA (来自 reports/vt_list.json, IDA 恢复)
KNOWN = {
    0x27E7360: 'CCountry', 0x2936CC0: 'CState', 0x2971B18: 'CProvince',
    0x297EA60: 'CCharacter', 0x295A2B0: 'CArmy', 0x29530D8: 'CUnit',
    0x27EB3D0: 'CDecision', 0x27D4990: 'CEffect', 0x27D55F0: 'CTrigger',
    0x2721158: 'CCurrentGameState', 0x27210E0: 'CGameState',
    0x2A133D8: 'CWorldTensionPopUpWindow',
}

JS = '''
var base = Process.enumerateModules()[0].base;
var gsGlobal = base.add(0x332F260);
var KNOWN = %s;
var KNOWN_JS = {};
Object.keys(KNOWN).forEach(function(k){ KNOWN_JS[(parseInt(k,10)).toString()] = KNOWN[k]; });

function vtName(p) {
    try {
        var nm = Process.findModuleByAddress(p);
        if (!nm) return null;
        if (nm.name !== 'hoi4.exe') return null;
        var rva = p.sub(base).toInt32() >>> 0;
        return KNOWN_JS[String(rva)] || ('rva:0x' + rva.toString(16));
    } catch (e) { return null; }
}

rpc.exports.dump = function () {
    var out = [];
    var gs;
    try { gs = gsGlobal.readPointer(); } catch (e) { return {err: 'read global: ' + e}; }
    if (gs.isNull()) return {err: 'CGameState is null'};
    out.push('CGameState = ' + gs);
    for (var off = 0; off < 0x1200; off += 8) {
        var v;
        try { v = gs.add(off).readPointer(); } catch (e) { break; }
        if (v.isNull()) continue;
        var u = v.toString();
        var s = '  +0x' + ('000' + off.toString(16)).slice(-4) + ' = ' + u;
        var nm = vtName(v);
        if (nm) s += '   <-- ' + nm;
        out.push(s);
    }
    return {lines: out};
};
''' % json.dumps({str(k): v for k, v in KNOWN.items()})

def wait_for_map(timeout=300):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            txt = open(GAMELOG, encoding='utf-8', errors='ignore').read()
            if 'Launching SINGLEPLAYER-game' in txt:
                return True
        except Exception:
            pass
        time.sleep(0.4)
    return False

def main():
    pid = frida.spawn([EXE, '-continuelastsave', '-gdpr-compliant'])
    session = frida.attach(pid)
    script = session.create_script(JS)
    script.load()
    print('[spawn] pid=%d' % pid, flush=True)
    frida.resume(pid)
    ok = wait_for_map()
    print('[map] 进入地图 = %s' % ok, flush=True)
    time.sleep(3)
    r = script.exports_sync.dump()
    if 'err' in r:
        print('[dump] ' + r['err'])
    else:
        for ln in r['lines']:
            print(ln)
    try:
        frida.kill(pid)
    except Exception:
        pass

main()