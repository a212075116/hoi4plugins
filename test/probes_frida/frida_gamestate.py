import frida, sys, time, json

EXE = r"D:\\SteamLibrary\\steamapps\\common\\Hearts of Iron IV\hoi4.exe"

SCRIPT = r"""
const m = Process.enumerateModules()[0];
const B = m.base;
send({t:"base", base: B.toString(), size: m.size});

const RVA_GLOBAL = 0x332F260;
const RVA_VT_MAIN = 0x2721158;
const RVA_VT_SEC  = 0x27211B0;

function probe(tag) {
    try {
        const slot = B.add(RVA_GLOBAL);
        const obj = slot.readPointer();
        if (obj.isNull()) { send({t:"probe", tag:tag, state:"null"}); return; }
        const vt0 = obj.readPointer();
        const vt1 = obj.add(8).readPointer();
        const want0 = B.add(RVA_VT_MAIN);
        const want1 = B.add(RVA_VT_SEC);
        send({
            t:"probe", tag:tag,
            obj: obj.toString(),
            vt0: vt0.toString(), want0: want0.toString(), ok0: vt0.equals(want0),
            vt1: vt1.toString(), want1: want1.toString(), ok1: vt1.equals(want1),
        });
        // 转储前 0x40 字节
        send({t:"dump", tag:tag, hex: hexdump(obj, {length: 0x40, header:false, ansi:false})});
    } catch (e) {
        send({t:"probe", tag:tag, state:"err", msg: e.message});
    }
}

setTimeout(function(){ probe("first"); }, 400);
setInterval(function(){ probe("later"); }, 12000);
"""

def on_message(msg, data):
    if msg["type"] != "send":
        print("[frida]", msg)
        return
    p = msg["payload"]
    t = p.get("t")
    if t == "base":
        print("[BASE] %s size=%d" % (p["base"], p["size"]))
    elif t == "probe":
        if p.get("state"):
            print("[%s] %s" % (p["tag"], p["state"]))
        else:
            print("[%s] obj=%s" % (p["tag"], p["obj"]))
            print("        vt0=%s  want=%s  MATCH=%s" % (p["vt0"], p["want0"], p["ok0"]))
            print("        vt1=%s  want=%s  MATCH=%s" % (p["vt1"], p["want1"], p["ok1"]))
    elif t == "dump":
        print("[%s] obj dump:" % p["tag"])
        for ln in p["hex"].split(chr(10)):
            print("        " + ln)

pid = frida.spawn([EXE])
print("[*] spawned pid", pid)
session = frida.attach(pid)
script = session.create_script(SCRIPT)
script.on("message", on_message)
script.load()
frida.resume(pid)
print("[*] resumed")
time.sleep(45)
try:
    session.detach()
except Exception:
    pass
print("[*] done")