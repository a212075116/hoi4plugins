import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_findstr.js', force_spawn=False, wait=False)
time.sleep(0.5)
e = sc.exports_sync
t0 = time.time()
while time.time() - t0 < 25:
    try: e.u32(0x1000); break
    except Exception: time.sleep(1)
# 24c2080: movdqa xmm0,[rip+0x255998]  指令长 8, 下一条 24c2088
a = e.rip(0x24c2080, 8, 0x255998)
# 24c208e: movups xmm0,[rip+0x48ec9b]  指令长 8, 下一条 24c2096
b = e.rip(0x24c208e, 8, 0x48ec9b)
print('常量 A (0x24c2080 引用) = rva 0x%x' % a)
print(e.hex(a, 16))
print('常量 B (0x24c208e 引用) = rva 0x%x' % b)
print(e.hex(b, 16))
