# -*- coding: utf-8 -*-
# 用 frida spawn hoi4.exe，非侵入式检查模块与基址
import frida, time, sys, json
W = r'D:\\SteamLibrary\\steamapps\\common\\Hearts of Iron IV'
local = frida.get_local_device()
print('spawning hoi4.exe ...')
pid = local.spawn([r'%s\hoi4.exe' % W], cwd=W)
print('spawned pid =', pid)
session = local.attach(pid)
js = '''
  var mods = Process.enumerateModules();
  var main = mods[0];
  send({ modules: mods.length,
         main: main.name,
         base: main.base.toString(),
         size: main.size,
         path: main.path });
'''
sc = session.create_script(js)
msgs = []
sc.on('message', lambda m, d: msgs.append(m))
sc.load()
time.sleep(2)
print('probe:', json.dumps(msgs[:1], ensure_ascii=False)[:600])
print('resuming ...')
local.resume(pid)
time.sleep(20)
try:
    procs = {p.pid: p.name for p in local.enumerate_processes()}
    print('alive:', procs.get(pid, 'GONE'))
except Exception as e:
    print('enum err', e)
try:
    session.detach()
    print('detached')
except Exception as e:
    print('detach err', e)