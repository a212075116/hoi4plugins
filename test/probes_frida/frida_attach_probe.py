# -*- coding: utf-8 -*-
# 附加到运行中的 hoi4，确认基址与虚表内容
import frida, time, json, sys
PID = int(sys.argv[1]) if len(sys.argv) > 1 else 41224
local = frida.get_local_device()
sess = local.attach(PID)
print('attached to', PID)
js = r'''
  var m = Process.enumerateModules().filter(function(x){
      return x.name.toLowerCase().indexOf('hoi4') === 0; });
  var main = m[0];
  var out = { name: main.name, base: main.base.toString(),
              size: main.size, path: main.path,
              allMods: Process.enumerateModules().length };
  // 静态 imagebase 假定为 0x140000000，比较实际基址
  out.staticBase = '0x140000000';
  send(out);
  '''
sc = sess.create_script(js)
msgs = []
sc.on('message', lambda m, d: msgs.append(m))
sc.load()
time.sleep(2)
for m in msgs[:2]:
    print(json.dumps(m.get('payload', m), ensure_ascii=False, indent=1)[:1200])
sess.detach()
print('detached OK')