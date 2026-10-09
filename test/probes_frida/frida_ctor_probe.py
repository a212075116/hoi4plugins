# -*- coding: utf-8 -*-
# 动态验证：在疑似构造/析构函数入口读 this，检查 [this] 是否等于虚表地址
import frida, time, json, sys
PID = int(sys.argv[1]) if len(sys.argv) > 1 else 41224
DUR = int(sys.argv[2]) if len(sys.argv) > 2 else 25
RUN = int(sys.argv[3]) if len(sys.argv) > 3 else 15   # 运行时长
STATIC_BASE = 0x140000000
# (符号, 疑似函数静态地址, 被引用的虚表静态地址)
CASES = [
    ('CUnit',                 0x140BF88A0, 0x1429530D8),
    ('CUnit',                 0x140BF8B50, 0x1429530D8),
    ('CUnit',                 0x140BF8ED0, 0x1429530D8),
    ('CEffect',               0x14053CF00, 0x1427D4990),
    ('CEffect',               0x14053CFD0, 0x1427D4990),
    ('CEffect',               0x14053D190, 0x1427D4990),
    ('CPdxMouse',             0x1423843D0, 0x142B59550),
    ('CPdxMouse(vfunc_0)',    0x142384520, 0x142B59550),
    ('CScriptedEffectTemplate', 0x14012B940, 0x14271B710),
    ('CScriptedEffectTemplate', 0x140130DE0, 0x14271B710),
]
local = frida.get_local_device()
sess = local.attach(PID)
js = '''
  var base = Process.enumerateModules().filter(function(x){
      return x.name.toLowerCase() === 'hoi4.exe'; })[0].base;
  var delta = base.sub('0x140000000');
  var cases = CASES_JSON;
  var results = {};
  cases.forEach(function(c){
      var fnAddr = base.add(c.fn - 0x140000000);
      var vtAddr = base.add(c.vt - 0x140000000);
      var key = c.cls + '@' + fnAddr.toString();
      results[key] = { cls: c.cls, fn: fnAddr.toString(), vt: vtAddr.toString(),
                       calls: 0, match: 0, mismatch: 0, sampleThis: null,
                       sampleSlot0: null, err: null };
      try {
          Interceptor.attach(fnAddr, {
              onEnter: function(args) {
                  var r = results[key];
                  r.calls++;
                  var thisp = args[0];
                  if (thisp.isNull()) return;
                  try {
                      var s0 = thisp.readPointer();
                      if (s0.equals(vtAddr)) {
                          r.match++;
                          if (r.sampleThis === null) {
                              r.sampleThis = thisp.toString();
                              r.sampleSlot0 = s0.toString();
                          }
                      } else {
                          r.mismatch++;
                      }
                  } catch (e) { r.err = String(e); }
              }
          });
      } catch (e) { results[key].err = 'attach: ' + e; }
  });
  setTimeout(function(){
      send({ delta: delta.toString(), results: results });
  }, RUN_MS);
  '''.replace('CASES_JSON', json.dumps([
      {'cls': a, 'fn': b, 'vt': c} for a, b, c in CASES])).replace('RUN_MS', str(RUN*1000))
sc = sess.create_script(js)
msgs = []
sc.on('message', lambda m, d: msgs.append(m))
sc.load()
print('hooked, observing %d s ...' % RUN)
time.sleep(RUN + 4)
p = msgs[0].get('payload') if msgs else None
if p:
    print('delta =', p['delta'])
    for k, r in p['results'].items():
        print('')
        print('%s  fn=%s vt=%s' % (r['cls'], r['fn'], r['vt']))
        print('   calls=%-6d match=%-6d mismatch=%-6d' % (r['calls'], r['match'], r['mismatch']))
        if r['sampleThis']:
            print('   样例 this=%s  [this]=%s' % (r['sampleThis'], r['sampleSlot0']))
        if r['err']:
            print('   err=%s' % r['err'])
else:
    print('no payload', msgs[:2])
sess.detach()
print('detached')