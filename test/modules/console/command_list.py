import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/exec_console_command.js', force_spawn=False)
time.sleep(0.3)
e = sc.exports_sync
print('=== 含 crash 的控制台命令 ===')
print(e.listCmds('crash'))
print()
print('=== 含 dump 的 ===')
print(e.listCmds('dump'))
