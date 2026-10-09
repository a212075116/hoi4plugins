import frida, sys, time, json

EXE = r"C:\Users\a2120\Documents\Paradox Interactive\Hearts of Iron IV\mod\bakaifa\hoi4.exe"
CWD = r"D:\\SteamLibrary\\steamapps\\common\\Hearts of Iron IV"

JS = r"""
var n = 0;
Process.setExceptionHandler(function (d) {
    n++;
    if (n > 12) return false;
    console.log("[EXC " + n + "] type=" + d.type + " addr=" + d.address);
    try {
        console.log("   pc=" + d.context.pc + " sp=" + d.context.sp);
        var bt = Thread.backtrace(d.context, Backtracer.FUZZY);
        for (var i = 0; i < bt.length && i < 14; i++) {
            var s = "";
            try { s = DebugSymbol.fromAddress(bt[i]).toString(); } catch (e) { s = "?"; }
            console.log("   #" + i + " " + bt[i] + "  " + s);
        }
    } catch (e) { console.log("   (bt failed: " + e + ")"); }
    return true;
});
console.log("[*] exception handler armed");
"""

def main():
    pid = frida.spawn([EXE, "-gdpr-compliant"], cwd=CWD)
    print("[*] spawned pid =", pid, flush=True)
    session = frida.attach(pid)
    script = session.create_script(JS)
    script.on("message", lambda m, data: print(m.get("payload", m), flush=True))
    script.load()
    frida.resume(pid)
    print("[*] resumed", flush=True)
    for i in range(40):
        time.sleep(1)
        try:
            # 探测进程是否还在
            frida.attach(pid).detach()
        except Exception:
            print("[*] process gone after", i + 1, "s", flush=True)
            break
    else:
        print("[*] still alive after 40 s", flush=True)
    try: frida.kill(pid)
    except Exception: pass

main()