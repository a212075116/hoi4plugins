# -*- coding: utf-8 -*-
# spawn -> 在 resume 之前装 hook -> resume -> 长窗口观察 -> 优雅退出
# 严格约束：单一 frida 会话，不做内存扫描（会拖死游戏）
import frida, time, json, sys
EXE = r'D:\SteamLibrary\steamapps\common\Hearts of Iron IV\hoi4.exe'
CWD = r'D:\SteamLibrary\steamapps\common\Hearts of Iron IV'
DUR = int(sys.argv[1]) if len(sys.argv) > 1 else 2400
OUT = 'reports/live_objects3.json'
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
print('specs = %d 个，窗口 %d s' % (len(specs), DUR), flush=True)
local = frida.get_local_device()
print('spawning ...', flush=True)
pid = local.spawn([EXE], cwd=CWD)
print('pid =', pid, flush=True)
sess = local.attach(pid)
js = '''
  var specs = SPECS_JSON;
  var recs = {};
  function install() {
      var m = Process.enumerateModules().filter(function(x){
          return x.name.toLowerCase() === 'hoi4.exe'; })[0];
      if (!m) return 'no module';
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
          } catch (e) { fail++; }
      });
      send({ installed: ok, failed: fail, base: m.base.toString() });
      return 'ok=' + ok + ' fail=' + fail;
  }
  rpc.exports = { install: install, dump: function(){ return recs; } };
  setInterval(function(){ send({ snapshot: true, recs: recs }); }, 20000);
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
        print('[JS] hooks installed = %d  failed = %d  base = %s'
              % (p['installed'], p['failed'], p['base']), flush=True)
    if p.get('snapshot'):
        state['recs'] = p['recs']
        hit = [v for v in p['recs'].values() if v['calls']]
        print(time.strftime('%H:%M:%S') + '  有构造=%d : %s' % (len(hit),
              ', '.join('%s=%d' % (v['cls'], v['calls']) for v in hit[:12]) or '(无)'), flush=True)
sc.on('message', on_msg)
sc.load()
# 关键：resume 之前装 hook，才能捕获启动期对象
res = sc.exports_sync.install()
print('install() ->', res, flush=True)
print('resuming ...', flush=True)
local.resume(pid)
print('>>> 游戏已启动，RTTI hook 已就位（含启动期）<<<', flush=True)
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
    print('  %-14s slots=%-3d calls=%-7d match=%-7d mismatch=%-6d unread=%-6d'
          % (x['cls'], x['slots'], x['calls'], x['match'], x['mismatch'], x['unreadable']), flush=True)
print('写盘:', OUT, flush=True)
try:
    sc.unload(); print('unloaded', flush=True)
except Exception as e:
    print('unload fail:', e, flush=True)
try:
    sess.detach(); print('detached', flush=True)
except Exception as e:
    print('detach fail:', e, flush=True)