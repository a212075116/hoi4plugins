import sys, time, importlib.util, os
os.chdir(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
fh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_addtoken.js', force_spawn=False)
time.sleep(0.5)
e = sc.exports_sync
print('=== 关键验证: 用新 id 反查名字 ===')
for i in (70279, 70278, 70280):
    print('  ' + e.nameOfId(i))
print()
print('=== 再注册一个, 看 id 是否递增 ===')
print(e.addToken('my_test_token_xyz'))
print('  ' + e.nameOfId(70280))
print()
print('=== 再次注册同名, 看是否返回同一个 id (幂等) ===')
print(e.addToken('set_camera_height'))
