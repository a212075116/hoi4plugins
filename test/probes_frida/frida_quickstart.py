import frida, sys, time, struct

EXE = r"D:\\SteamLibrary\\steamapps\\common\\Hearts of Iron IV\hoi4.exe"
ARGS = [EXE, "-quickstart", "-gdpr-compliant"]
print("[*] args:", ARGS[1:])

SCRIPT = r"""
const m = Process.enumerateModules()[0];
const B = m.base;
function snap(tag){
  const obj = B.add(0x332F260).readPointer();
  if (obj.isNull()) { send({t:"null",tag:tag}); return; }
  let buf=null; try{ buf = obj.readByteArray(0x1100); }catch(e){}
  send({t:"snap", tag:tag, base:B.toString(), obj:obj.toString(), bytes:buf}, buf);
}
for (const ms of [20000, 45000, 75000, 110000]) setTimeout(()=>snap("t"+ms), ms);
"""

snaps=[]
def on_message(msg, data):
    if msg["type"]!="send": print("[frida]", msg); return
    p=msg["payload"]
    if p.get("t")=="snap":
        print("[SNAP %s] obj=%s len=%d" % (p["tag"], p["obj"], len(data or b"")))
        snaps.append((p["tag"], p["base"], p["obj"], data))
    elif p.get("t")=="null": print("[NULL %s]" % p["tag"])

pid = frida.spawn(ARGS)
s = frida.attach(pid)
sc = s.create_script(SCRIPT)
sc.on("message", on_message)
sc.load()
frida.resume(pid)
print("[*] pid", pid)
time.sleep(125)

for tag, base, obj, data in snaps:
    if not data: continue
    b=int(base,16); n=len(data)//8
    q=struct.unpack("<%dQ"%n, data[:n*8])
    nz=[(i*8,q[i]) for i in range(n) if q[i] not in (0,0x0101010101010101)]
    print("=== %s obj=%s  非空 qword %d/%d ===" % (tag,obj,len(nz),n))
    for o,v in nz[:28]:
        tail = ""
        if b <= v < b+0x4000000: tail = "  <- 指向 hoi4 内 RVA 0x%X" % (v-b)
        print("   +0x%04X = 0x%X%s" % (o, v, tail))
    # 尝试找数组
    for off in range(0, n-2):
        ptr,sz,cap=q[off],q[off+1],q[off+2]
        if 50<=sz<=1200 and 0x10000<ptr<0x7fffffffffff and (cap==0 or sz<=cap<=sz*4+64):
            try:
                first=q[0] if False else None
            except Exception: pass
            print("   [数组?] +0x%04X ptr=0x%X size=%d cap=%d" % (off*8,ptr,sz,cap))

try: s.detach()
except Exception: pass