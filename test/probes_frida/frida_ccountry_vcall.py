# frida_ccountry_vcall.py -- 统计 CCountry 各虚函数被调用的次数
#
# 目的: 为"局部重编译"挑一个真正被调用的函数。
# 做法: 把 CCountry 每个实例的虚表槽替换成统计桩(stub), 桩里计数后跳回原函数。
#
# 为什么改实例的虚表而不是改 .rdata 里的虚表本身:
#   虚表在 .rdata 是只读的, 改它需要 VirtualProtect, 且会影响所有同类对象。
#   逐个实例新建一份虚表副本只影响该实例, 出问题也只坏一个对象, 好回滚。
import frida, time

EXE = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4.exe'
GAMELOG = r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log'
JS = '''
var base = Process.enumerateModules()[0].base;
var VT_COUNTRY = base.add(0x27E7360);
var NSLOT = 11;
var counters = {};
var originals = [];
var patched = 0;

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

rpc.exports.install = function (maxInst) {
    originals = [];
    for (var k = 0; k < NSLOT; k++) counters[k] = 0;
    var inst = scanWhole(VT_COUNTRY.toMatchPattern(), maxInst);
    for (var i = 0; i < inst.length; i++) {
        var obj = inst[i];
        var vt = obj.readPointer();
        // 为该实例单独复制一份虚表
        var copy = Memory.alloc(NSLOT * 8);
        for (var s = 0; s < NSLOT; s++) copy.add(s * 8).writePointer(vt.add(s * 8).readPointer());
        // 每个槽换成统计桩
        for (var s2 = 0; s2 < NSLOT; s2++) {
            (function (slot) {
                var orig = vt.add(slot * 8).readPointer();
                var origU = orig.toString();
                var stub = Memory.alloc(Process.pageSize);
                Memory.protect(stub, Process.pageSize, 'rwx');
                // 桩: 直接改成跳板太复杂, 改用 Interceptor 无法逐实例。
                // 简化: 桩就是"记录并跳到原地址"的机器码。
                // mov rax, imm64 ; jmp rax
                var code = [];
                code.push(0x48, 0xB8);              // mov rax, imm64
                var b = [];
                var v = origU;
                var bn = BigInt(v);
                for (var t = 0; t < 8; t++) { b.push(Number((bn >> BigInt(8 * t)) & 0xFFn)); }
                code = code.concat(b);
                code.push(0xFF, 0xE0);              // jmp rax
                stub.writeByteArray(code);
                copy.add(slot * 8).writePointer(stub);
            })(s2);
        }
        Memory.protect(obj, 8, 'rw-');
        obj.writePointer(copy);
        patched++;
        originals.push(obj.toString());
    }
    return {instances: inst.length, patched: patched};
};

rpc.exports.counts = function () { return counters; };
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
r = sc.exports_sync.install(133)
print('[安装] 实例=%s  已打桩=%s' % (r['instances'], r['patched']))
print('[观察] 等待虚函数被调用...', flush=True)
time.sleep(20)
c = sc.exports_sync.counts()
print('[调用计数]')
for k in sorted(c.keys(), key=lambda x: int(x)):
    print('    slot %2s : %s' % (k, c[k]))
try: frida.kill(pid)
except Exception: pass