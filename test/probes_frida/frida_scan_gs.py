import frida, sys, time, json

EXE = r"D:\\SteamLibrary\\steamapps\\common\\Hearts of Iron IV\hoi4.exe"

SCRIPT = r"""
const m = Process.enumerateModules()[0];
const B = m.base;

function snapshot() {
    const slot = B.add(0x332F260);
    const obj = slot.readPointer();
    if (obj.isNull()) { send({t:"null"}); return; }
    let buf;
    try { buf = obj.readByteArray(0x1000); } catch (e) { send({t:"err", m:e.message}); return; }
    send({t:"snap", base: B.toString(), obj: obj.toString(), bytes: buf}, buf);
}
setTimeout(snapshot, 9000);
setTimeout(snapshot, 30000);
"""

g = {"snaps": []}

def on_message(msg, data):
    if msg["type"] != "send":
        print("[frida]", msg); return
    p = msg["payload"]
    if p.get("t") == "snap":
        print("[SNAP] base=%s obj=%s len=%d" % (p["base"], p["obj"], len(data or b"")))
        g["snaps"].append({"base": p["base"], "obj": p["obj"], "data": data})
    elif p.get("t") == "err":
        print("[ERR]", p["m"])
    elif p.get("t") == "null":
        print("[NULL] CGameState 尚未创建")

pid = frida.spawn([EXE])
session = frida.attach(pid)
script = session.create_script(SCRIPT)
script.on("message", on_message)
script.load()
frida.resume(pid)
print("[*] resumed pid", pid)
time.sleep(48)
try: session.detach()
except Exception: pass

import struct
VT_CCountry = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x27E7360
for s in g["snaps"]:
    b = int(s["base"], 16); d = s["data"]
    if not d: continue
    n = len(d) // 8
    q = struct.unpack("<%dQ" % n, d[:n*8])
    print("=== 扫描 obj=%s（%d 个 qword），目标 CCountry vt RVA=0x%X ===" % (s["obj"], n, VT_CCountry))
    cands = []
    for off in range(0, n - 2):
        ptr, sz, cap = q[off], q[off+1], q[off+2]
        if 0x40 <= sz <= 2000 and ptr > 0x10000 and (cap == 0 or cap >= sz) and sz <= (1 << 20):
            cands.append((off*8, ptr, sz, cap))
    print("  候选 {ptr,size,cap} 结构 %d 个" % len(cands))
    for off, ptr, sz, cap in cands[:25]:
        print("    +0x%04X  ptr=0x%X  size=%d  cap=%d" % (off, ptr, sz, cap))