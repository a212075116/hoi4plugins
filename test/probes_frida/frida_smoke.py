# -*- coding: utf-8 -*-
# 验证 frida 注入：附加 explorer 并枚举模块
import frida, time
print('frida', frida.__version__)
local = frida.get_local_device()
procs = local.enumerate_processes()
target = next((p for p in procs if p.name.lower() == 'explorer.exe'), None)
print('target:', target.pid if target else None)
if target:
    s = local.attach(target.pid)
    js = 'var m = Process.enumerateModules();' \
         'send({count: m.length,' \
         '      first: m.slice(0,5).map(function(x){ return x.name; })});'
    script = s.create_script(js)
    got = []
    script.on('message', lambda msg, data: got.append(msg))
    script.load()
    time.sleep(1.5)
    print('result:', got[:1])
    s.detach()
    print('detached OK')