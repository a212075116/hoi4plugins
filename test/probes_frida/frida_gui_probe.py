# -*- coding: utf-8 -*-
# 在主菜单状态下 hook CGui 构造点，捕获实例并验证虚表
import frida, time, json, sys
PID = int(sys.argv[1]) if len(sys.argv) > 1 else 41224
RUN = int(sys.argv[2]) if len(sys.argv) > 2 else 20
CASES = [
    ('CGui',           0x142259B30, 0x142B3F4E0),
    ('CGui',           0x142259EA0, 0x142B3F4E0),
    ('CGuiAnimReload', 0x142235600, 0x142B3D898),
]
local = frida.get_local_device()
sess = local.attach(PID)
js = '''
  var base = Process.enumerateModules().filter(function(x){
      return x.name.toLowerCase() === 'hoi4.exe'; })[0].base;
  var cases = CASES_JSON;
  var out = [];
  cases.forEach(function(c){
      var fnAddr = base.add(c.fn - 0x140000000);
      var vtAddr = base.add(c.vt - 0x140000000);
      var rec = { cls: c.cls, fn: fnAddr.toString(), vt: vtAddr.toString(),
                  calls: 0, match: 0, mismatch: 0, others: {},
                  firstThis: null, firstSlot0: null, err: null };
      out.push(rec);
      try {
          Interceptor.attach(fnAddr, {
              onEnter: function(args) {
                  rec.calls++;
                  var t = args[0];
                  if (t.isNull()) return;
                  try {
                      var s0 = t.readPointer();
                      if (rec.firstThis === null) {
                          rec.firstThis = t.toString();
                          rec.firstSlot0 = s0.toString();
                      }
                      if (s0.equals(vtAddr)) rec.match++;
                      else {
                          rec.mismatch++;
                          var k = s0.toString();
                          rec.others[k] = (rec.others[k] || 0) + 1;
                      }
                  } catch (e) { rec.err = String(e); }
              }
          });
      } catch (e) { rec.err = 'attach: ' + e; }
  });
  setTimeout(function(){ send({ delta: base.sub('0x140000000').toString(), recs: out }); }, RUN_MS);
  '''.replace('CASES_JSON', json.dumps([{'cls': a, 'fn': b, 'vt': c} for a, b, c in CASES])) \
     .replace('RUN_MS', str(RUN*1000))
sc = sess.create_script(js)
msgs = []
sc.on('message', lambda m, d: msgs.append(m))
sc.load()
print('observing %d s ...' % RUN)
time.sleep(RUN + 4)
p = msgs[0].get('payload') if msgs else None
if p:
    print('delta =', p['delta'])
    for r in p['recs']:
        print('')
        print('%s  fn=%s  vt=%s' % (r['cls'], r['fn'], r['vt']))
        print('   calls=%-5d match=%-5d mismatch=%-5d' % (r['calls'], r['match'], r['mismatch']))
        if r['firstThis']:
            print('   first this=%s  [this]=%s' % (r['firstThis'], r['firstSlot0']))
        for k, v in list(r['others'].items())[:5]:
            print('      other [this]=%s x%d' % (k, v))
        if r['err']: print('   err=', r['err'])
else:
    print('no payload', msgs[:2])
sess.detach()