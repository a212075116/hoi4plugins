import frida, sys, time

EXE = r"C:\Users\a2120\Documents\Paradox Interactive\Hearts of Iron IV\mod\bakaifa\hoi4.exe"
CWD = r"D:\\SteamLibrary\\steamapps\\common\\Hearts of Iron IV"

JS = r"""
var main = Process.enumerateModules()[0];
var base = main.base;
console.log("[*] main module: " + main.name + " base=" + base + " size=0x" + main.size.toString(16));
var n = 0;
Process.setExceptionHandler(function (d) {
    n++;
    if (n > 3) return false;
    if (d.type !== "access-violation") return true;
    console.log("[AV] pc=" + d.context.pc + "  rva=0x" + d.context.pc.sub(base).toString(16));
    console.log("     addr=" + d.address + "  rva=0x" + d.address.sub(base).toString(16));
    console.log("     rax=" + d.context.rax + " rcx=" + d.context.rcx + " rdx=" + d.context.rdx);
    var bt = Thread.backtrace(d.context, Backtracer.FUZZY);
    for (var i = 0; i < bt.length && i < 10; i++) {
        var r = "?";
        try { r = "0x" + bt[i].sub(base).toString(16); } catch (e) {}
        var m = Process.findModuleByAddress(bt[i]);
        console.log("     #" + i + " " + bt[i] + "  rva=" + r + "  in=" + (m ? m.name : "?"));
    }
    return false;
});
console.log("[*] armed");
"""

pid = frida.spawn([EXE, "-gdpr-compliant"], cwd=CWD)
print("[*] pid", pid, flush=True)
session = frida.attach(pid)
script = session.create_script(JS)
script.on("message", lambda m, data: print(m.get("payload", m), flush=True))
script.load()
frida.resume(pid)
for i in range(45):
    time.sleep(1)
    try: frida.attach(pid).detach()
    except Exception:
        print("[*] gone after", i + 1, "s", flush=True)
        break
try: frida.kill(pid)
except Exception: pass