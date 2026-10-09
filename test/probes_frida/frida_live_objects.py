# -*- coding: utf-8 -*-
# 常驻 hook：等用户加载存档/操作，记录游戏对象的实例创建
import frida, time, json, sys, os
PID = int(sys.argv[1]) if len(sys.argv) > 1 else 41224
DUR = int(sys.argv[2]) if len(sys.argv) > 2 else 900
OUT = sys.argv[3] if len(sys.argv) > 3 else 'reports/live_objects.json'
T = json.load(open('reports/ctor_targets.json', encoding='utf-8'))
# 去重：同一构造函数可能对应多个虚表，保留 (cls, ctor, vt) 三元组
specs, seen = [], set()
for x in T:
    key = (x['cls'], x['ctor'], x['rva'])
    if key in seen:
        continue
    seen.add(key)
    specs.append({'cls': x['cls'], 'rva': x['rva'], 'n': x['n'], 'ctor': x['ctor']})
print('hooking %d (class,ctor,vftable) 组合' % len(specs))
local = frida.get_local_device()
sess = local.attach(PID)
js = '''
  var m = Process.enumerateModules().filter(function(x){
      return x.name.toLowerCase() === 'hoi4.exe'; })[0];
  var specs = SPECS_JSON;
  var recs = {};
  specs.forEach(function(sp){
      var key = sp.cls + '|' + sp.rva;
      var r = recs[key] || (recs[key] = {
          cls: sp.cls, rva: sp.rva, n: sp.n, ctors: [],
          calls: 0, match: 0, mismatch: 0, firstThis: null, firstSlot0: null,
          otherSlots: {} });
      if (r.ctors.indexOf(sp.ctor) < 0) r.ctors.push(sp.ctor);
      var fnAddr = m.base.add(sp.ctor - 0x140000000);
      var vtAddr = m.base.add(sp.rva);
      try {
          Interceptor.attach(fnAddr, {
              onEnter: function(args) {
                  r.calls++;
                  var t = args[0];
                  if (t.isNull()) return;
                  try {
                      var s0 = t.readPointer();
                      if (r.firstThis === null) {
                          r.firstThis = t.toString();
                          r.firstSlot0 = s0.toString();
                      }
                      if (s0.equals(vtAddr)) r.match++;
                      else {
                          r.mismatch++;
                          var k = s0.toString();
                          r.otherSlots[k] = (r.otherSlots[k] || 0) + 1;
                      }
                  } catch (e) {}
              }
          });
      } catch (e) {}
  });
  // 每 20 秒把快照写到宿主
  var tick = 0;
  setInterval(function(){
      tick++;
      send({ snapshot: tick, recs: recs });
  }, 20000);
  setTimeout(function(){ send({ final: true, recs: recs }); }, FINAL_MS);
  '''.replace('SPECS_JSON', json.dumps(specs)) \
     .replace('FINAL_MS', str(DUR * 1000))
sc = sess.create_script(js)
state = {'last': None}
def on_msg(msg, data):
    p = msg.get('payload')
    if not p:
        return
    if p.get('final'):
        state['last'] = p['recs']
        print('[FINAL RECEIVED]')
    elif p.get('snapshot'):
        state['last'] = p['recs']
        hit = [(k, v) for k, v in p['recs'].items() if v['calls']]
        print('[snap %d] 有调用的类 = %d' % (p['snapshot'], len(hit)))
        for k, v in hit[:12]:
            print('     %-24s calls=%-7d match=%-7d' % (v['cls'], v['calls'], v['match']))
sc.on('message', on_msg)
sc.load()
print('hooks installed; waiting up to %d s ...' % DUR)
t0 = time.time()
while time.time() - t0 < DUR + 30:
    if state['last'] and any(v['calls'] for v in state['last'].values()):
        # 已有数据；继续等到时间结束或收到 final
        pass
    time.sleep(3)
    if time.time() - t0 > DUR + 25:
        break
recs = state['last'] or {}
summary = []
for k, v in recs.items():
    summary.append({'key': k, 'cls': v['cls'], 'rva': v['rva'], 'slots': v['n'],
                    'ctors': v['ctors'], 'calls': v['calls'], 'match': v['match'],
                    'mismatch': v['mismatch'], 'firstThis': v['firstThis'],
                    'firstSlot0': v['firstSlot0'],
                    'otherSlots': v['otherSlots']})
summary.sort(key=lambda x: -x['calls'])
json.dump(summary, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('')
print('=== 结果（按调用次数）===')
for x in summary[:40]:
    if x['calls']:
        print('  %-24s slots=%-3d calls=%-7d match=%-7d mismatch=%-6d first this=%s'
              % (x['cls'], x['slots'], x['calls'], x['match'], x['mismatch'], x['firstThis']))
print('')
print('有实例创建的类数 = %d / %d' % (sum(1 for x in summary if x['calls']), len(summary)))
print('写盘:', OUT)
sess.detach()