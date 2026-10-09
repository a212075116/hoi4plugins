# -*- coding: utf-8 -*-
# 运行时验证：读虚表并与静态分析对比
import frida, time, json, sys
PID = int(sys.argv[1]) if len(sys.argv) > 1 else 41224
STATIC_BASE = 0x140000000
# 静态分析得到的目标（来自 ida_vt_boundary / ida_vfunc_verify2）
TARGETS = [
    ('??_7CEffect@@6B@',            0x1427D4990, 25),
    ('??_7CScriptedEffectTemplate@@6B@', 0x14271B710, 25),
    ('??_7CPdxMouse@@6B@',          0x142B59550, 33),
    ('??_7CUnit@@6B@',              0x1429530D8, 58),
]
local = frida.get_local_device()
sess = local.attach(PID)
js = '''
  var m = Process.enumerateModules().filter(function(x){
      return x.name.toLowerCase() === 'hoi4.exe'; })[0];
  var out = { base: m.base.toString(), delta: m.base.sub('0x140000000').toString(),
              tables: [], totalMods: Process.enumerateModules().length };
  var targets = TARGETS_JSON;
  targets.forEach(function(t){
      var addr = m.base.add(t.off - 0x140000000);
      var slots = [];
      for (var k = 0; k < t.len; k++) {
          var p = addr.add(k*8).readPointer();
          slots.push(p.toString());
      }
      // 读末槽之后一格（应当是下一张表的 COL 指针）
      var nxt = addr.add(t.len*8).readPointer();
      out.tables.push({ sym: t.sym, addr: addr.toString(), slots: slots,
                        after: nxt.toString() });
  });
  send(out);
  '''.replace('TARGETS_JSON', json.dumps([
      {'sym': a, 'off': b, 'len': c} for a, b, c in TARGETS]))
sc = sess.create_script(js)
msgs = []
sc.on('message', lambda m, d: msgs.append(m))
sc.load()
time.sleep(2)
p = msgs[0].get('payload') if msgs else None
if p:
    print('runtime base =', p['base'], ' delta =', p['delta'])
    print('modules =', p['totalMods'])
    for t in p['tables']:
        print('')
        print('%s @ %s' % (t['sym'], t['addr']))
        for i, x in enumerate(t['slots']):
            print('   [%2d] %s' % (i, x))
        print('   >>after: %s' % t['after'])
else:
    print('no payload', msgs[:2])
sess.detach()
print('detached')