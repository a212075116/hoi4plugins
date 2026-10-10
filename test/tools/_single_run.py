import sys, time, importlib.util as iu
sys.path.insert(0, r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/tools')
s = iu.spec_from_file_location('fh', r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_frida/frida_host.py')
fh = iu.module_from_spec(s); s.loader.exec_module(fh)
# 单会话: 只用 _exec_cmd.js (它本身能执行命令), 全程不 detach 再 connect
pid = fh.find_pid()
print('pid=%s' % pid, flush=True)
pid, session, sc, fresh = fh.connect(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins/test/probes_js/_exec_cmd.js', force_spawn=False)
e = sc.exports_sync
time.sleep(0.5)
def msg(r):
    for ln in str(r).split(chr(10)):
        if 'out->message' in ln: return ln.split('=',1)[1].strip()
    return '?'
GS_JS = 'rpc.exports={gs:function(){var b=Process.getModuleByName("hoi4.exe").base.add(0x332F260).readPointer();return b.isNull()?null:b.toString();},rd:function(o,n){var g=Process.getModuleByName("hoi4.exe").base.add(0x332F260).readPointer();var a=[];for(var i=0;i<n;i++)a.push(g.add(o+i*4).readS32());return a.join(",");}};'
gsc = session.create_script(GS_JS)
gsc.load()
t0 = time.time()
while time.time() - t0 < 120:
    try:
        gs = gsc.exports_sync.gs()
        if gs: break
    except Exception: pass
    time.sleep(1)
print('CGameState=%s (%.0fs)' % (gs, time.time()-t0), flush=True)
time.sleep(15)
print('--- 暂停状态检查 (不发 auto_unpause) ---', flush=True)
print('  日期: ' + msg(e.exec('setgamedate', [])), flush=True)
print('  派生: ' + str(gsc.exports_sync.rd(0x478, 5)), flush=True)
print('--- 设 510.6.7.0 (暂停下) ---', flush=True)
print('  ' + msg(e.exec('setgamedate', ['510.6.7.0'])), flush=True)
time.sleep(1)
print('  派生: ' + str(gsc.exports_sync.rd(0x478, 5)) + '   <- 应立即变化', flush=True)
print('--- 加减 45 天 ---', flush=True)
print('  ' + msg(e.exec('addtimefordays', ['45'])), flush=True)
time.sleep(1)
print('  派生: ' + str(gsc.exports_sync.rd(0x478, 5)), flush=True)
print('--- 恢复流逝, 观察 12 秒 ---', flush=True)
print('  ' + msg(e.exec('auto_unpause', ['2'])), flush=True)
for i in range(3):
    time.sleep(4)
    print('  T+%2ds 日期: %s' % ((i+1)*4, msg(e.exec('setgamedate', []))), flush=True)
print('--- 全部完成, detach ---', flush=True)
fh.detach(session)
print('OK', flush=True)
