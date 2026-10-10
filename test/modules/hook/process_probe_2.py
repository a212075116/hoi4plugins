import sys, time, importlib.util
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib')
spec = importlib.util.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/lib/frida_host.py')
fh = importlib.util.module_from_spec(spec); spec.loader.exec_module(fh)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/modules/hook/probe_process.js', force_spawn=False)
time.sleep(0.4)
e = sc.exports_sync
print(e.start())
# 用另一个态触发 crashme: 直接在本脚本里制造线程崩溃
sc2 = session.create_script("rpc.exports={go:function(){const t=new NativeFunction(Module.getExportByName('kernel32.dll','CreateThread'),'pointer',['pointer','ulong','pointer','pointer','ulong','pointer']);const cb=new NativeCallback(function(){ptr(0).writeU8(1);return 0;},'ulong',['pointer']);t(ptr(0),ptr(0),cb,ptr(0),ptr(0),ptr(0));return 'spawned';}}")
sc2.load()
try:
    print(sc2.exports_sync.go())
except Exception as ex:
    print('(预期) %s' % str(ex)[:100])
time.sleep(25)
