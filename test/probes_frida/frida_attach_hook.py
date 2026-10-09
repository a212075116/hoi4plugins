# -*- coding: utf-8 -*-
# 附加到已在运行的 hoi4，安装 hook（修正：显式调用 install），长期运行后优雅 detach
import frida, time, json, sys
PID = int(sys.argv[1])
DUR = int(sys.argv[2]) if len(sys.argv) > 2 else 1500
OUT = sys.argv[3] if len(sys.argv) > 3 else 'reports/live_objects2.json'
T = json.load(open('reports/ctor_targets.json', encoding='utf-8'))
WANT = ['CGameState','CCountry','CState','CProvince','CCharacter','CUnit','CArmy','CFleet',
        'CEffect','CTrigger','CDecision']
specs, seen = [], set()
for x in T:
    if x['cls'] not in WANT or x['cls'] == 'CModifier':
        continue
    key = (x['cls'], x['ctor'])
    if key in seen:
        continue
    seen.add(key)
    specs.append({'cls': x['cls'], 'rva': x['rva'], 'n': x['n'], 'ctor': x['ctor']})
print('将挂 %d 个 hook，观察 %d s' % (len(specs), DUR), flush=True)
local = frida.get_local_device()
sess = local.attach(PID)
print('attached to', PID, flush=True)
js = '''
  var specs = SPECS_JSON;
  var recs = {};
  function install() {
      var m = Process.enumerateModules().filter(function(x){
          return x.name.toLowerCase() === 'hoi4.exe'; })[0];
      if (!m) { send({ err: 'no module' }); return 'no module'; }
      var ok = 0, fail = 0;
      specs.forEach(function(sp){
          var key = sp.cls + '|' + sp.rva;
          var r = recs[key] || (recs[key] = {
              cls: sp.cls, rva: sp.rva, n: sp.n, ctors: [],
              calls: 0, match: 0, mismatch: 0, unreadable: 0,
              firstThis: null, firstSlot0: null, otherSlots: {} });
          if (r.ctors.indexOf(sp.ctor) < 0) r.ctors.push(sp.ctor);
          var fnAddr = m.base.add(sp.ctor - 0x140000000);
          var vtAddr = m.base.add(sp.rva);
          try {
              Interceptor.attach(fnAddr, {
                  onEnter: function(args) {
                      r.calls++;
                      var t = args[0];
                      if (t.isNull()) { r.unreadable++; return; }
                      var rg = null;
                      try { rg = Process.findRangeByAddress(t); } catch (e) {}
                      if (!rg || rg.protection.indexOf('r') < 0) { r.unreadable++; return; }
                      var s0;
                      try { s0 = t.readPointer(); } catch (e) { r.unreadable++; return; }
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
                  }
              });
              ok++;
          } catch (e) { fail++; send({ attachErr: sp.cls + ': ' + e }); }
      });
      send({ installed: ok, failed: fail, base: m.base.toString() });
      return 'ok=' + ok + ' fail=' + fail;
  }
  rpc.exports = { install: install, dump: function(){ return recs; } };
  setInterval(function(){ send({ snapshot: true, recs: recs }); }, 15000);
  '''.replace('SPECS_JSON', json.dumps(specs))
sc = sess.create_script(js)
state = {'recs': {}, 'installed': False}
def on_msg(msg, data):
    p = msg.get('payload')
    if not p:
        if msg.get('type') == 'error':
            print('[JS error]', msg.get('description'), flush=True)
        return
    if p.get('installed') is not None:
        state['installed'] = True
        print('[JS] >>> hooks installed = %d  failed = %d  base = %s'
              % (p['installed'], p['failed'], p['base']), flush=True)
    if p.get('attachErr'):
        print('[JS attachErr]', p['attachErr'], flush=True)
    if p.get('snapshot'):
        state['recs'] = p['recs']
        hit = [v for v in p['recs'].values() if v['calls']]
        print(time.strftime('%H:%M:%S') + '  有构造的类=%d : %s' % (len(hit),
              ', '.join('%s=%d' % (v['cls'], v['calls']) for v in hit[:10]) or '(无)'), flush=True)
sc.on('message', on_msg)
sc.load()
print('script loaded, calling install() ...', flush=True)
res = sc.exports_sync.install()
print('install() 返回:', res, flush=True)
print('>>> 现在可以操作游戏了 <<<', flush=True)
t0 = time.time()
while time.time() - t0 < DUR:
    time.sleep(5)
    try:
        recs = sc.exports_sync.dump()
        if recs:
            state['recs'] = recs
    except Exception as e:
        print('!! 连接中断:', e, flush=True)
        break
recs = state['recs'] or {}
summary = []
for k, v in recs.items():
    summary.append({'key': k, 'cls': v['cls'], 'rva': v['rva'], 'slots': v['n'],
                    'ctors': v['ctors'], 'calls': v['calls'], 'match': v['match'],
                    'mismatch': v['mismatch'], 'unreadable': v.get('unreadable', 0),
                    'firstThis': v['firstThis'], 'firstSlot0': v['firstSlot0'],
                    'otherSlots': v['otherSlots']})
summary.sort(key=lambda x: -x['calls'])
json.dump(summary, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('', flush=True)
print('=== 结果 ===', flush=True)
for x in summary:
    print('  %-14s slots=%-3d calls=%-7d match=%-7d mismatch=%-6d unread=%-6d first=%s'
          % (x['cls'], x['slots'], x['calls'], x['match'], x['mismatch'],
             x['unreadable'], x['firstThis']), flush=True)
print('写盘:', OUT, flush=True)
try:
    sc.unload(); print('script unloaded', flush=True)
except Exception as e:
    print('unload 失败:', e, flush=True)
try:
    sess.detach(); print('sess detached', flush=True)
except Exception as e:
    print('detach 失败:', e, flush=True)