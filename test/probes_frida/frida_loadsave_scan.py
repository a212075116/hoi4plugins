import frida, sys, time, struct

EXE = r"D:\\SteamLibrary\\steamapps\\common\\Hearts of Iron IV\hoi4.exe"
ARGS = [EXE, "-continuelastsave", "-gdpr-compliant"]

SCRIPT = r"""
const m = Process.enumerateModules()[0];
const B = m.base;
function snapshot(tag) {
    const obj = B.add(0x332F260).readPointer();
    if (obj.isNull()) { send({t:"null", tag:tag}); return; }
    let buf = null;
    try { buf = obj.readByteArray(0x1800); } catch (e) {}
    send({t:"snap", tag:tag, base:B.toString(), obj:obj.toString(), bytes: buf}, buf);
}
for (const ms of [15000, 35000, 60000, 95000, 130000]) setTimeout(() => snapshot("t"+ms), ms);
"""

snaps = []
def on_message(msg, data):
    if msg["type"] != "send":
        print("[frida]", msg); return
    p = msg["payload"]
    if p.get("t") == "snap":
        print("[SNAP %s] obj=%s len=%d" % (p["tag"], p["obj"], len(data or b"")))
        snaps.append((p["tag"], p["base"], p["obj"], data))
    elif p.get("t") == "null":
        print("[NULL %s] 尚未创建" % p["tag"])

pid = frida.spawn(ARGS)
session = frida.attach(pid)
script = session.create_script(SCRIPT)
script.on("message", on_message)
script.load()
frida.resume(pid)
print("[*] resumed pid", pid)
time.sleep(145)

VT = 0x27E7360   # CCountry vtable rva
def scan(tag, base, obj, data):
    if not data: return
    b = int(base, 16); n = len(data)//8
    q = struct.unpack("<%dQ" % n, data[:n*8])
    print("=== %s obj=%s (%d qword) ===" % (tag, obj, n))
    hits = 0
    for off in range(0, n-2):
        ptr, sz, cap = q[off], q[off+1], q[off+2]
        if 50 <= sz <= 1200 and 0x10000 < ptr < 0x7fffffffffff and (cap == 0 or (sz <= cap <= sz*4+64)):
            print("   cand +0x%04X ptr=0x%X size=%d cap=%d" % (off*8, ptr, sz, cap))
            hits += 1
            if hits >= 12: break
    if hits == 0:
        nz = [(i*8, q[i]) for i in range(n) if q[i] != 0 and q[i] != 0x0101010101010101]
        print("   无候选。非零字段 %d 个，前 30：" % len(nz))
        for o, v in nz[:30]:
            print("     +0x%04X = 0x%X" % (o, v))

for tag, base, obj, data in snaps:
    scan(tag, base, obj, data)
try: session.detach()
except Exception: pass
print("[*] done")