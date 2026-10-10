# -*- coding: utf-8 -*-
# spawn + 保守 hook，固定时长运行，结束前显式 detach（绝不允许外部强杀！）
import frida, time, json, sys, os, signal
EXE = r'D:\SteamLibrary\steamapps\common\Hearts of Iron IV\hoi4.exe'
CWD = r'D:\SteamLibrary\steamapps\common\Hearts of Iron IV'
DUR = int(sys.argv[1]) if len(sys.argv) > 1 else 1800
MODE = sys.argv[2] if len(sys.argv) > 2 else 'minimal'
OUT = 'reports/live_objects.json'
T = json.load(open('reports/ctor_targets.json', encoding='utf-8'))
WANT = ['CGameState','CCountry','CState','CProvince','CCharacter','CUnit','CArmy','CFleet',
        'CEffect','CTrigger','CDecision']
if MODE == 'minimal':
    WANT = ['CGameState','CCountry','CState']
specs, seen = [], set()
for x in T:
    if x['cls'] not in WANT or x['cls'] == 'CModifier':
        continue
    key = (x['cls'], x['ctor'])
    if key in seen:
        continue
    seen.add(key)
    specs.append({'cls': x['cls'], 'rva': x['rva'], 'n': x['n'], 'ctor': x['ctor']})
print('mode=%s  将挂 %d 个 hook，运行 %d s' % (MODE, len(specs), DUR), flush=True)
for sp in specs:
    print('   %-14s ctor=0x%X vt_rva=0x%X slots=%d' % (sp['cls'], sp['ctor'], sp['rva'], sp['n']), flush=True)
local = frida.get_local_device()
print('spawning ...', flush=True)
pid = local.spawn([EXE], cwd=CWD)
print('pid =', pid, flush=True)
sess = local.attach(pid)
js = '''
  var specs = SPECS_JSON;
  var recs = {};
  var m = null;
  function install() {
      m = Process.enumerateModules().filter(function(x){
          return x.name.toLowerCase() === 'hoi4.exe'; })[0];
      if (!m) { send({ err: 'no module' }); return; }
      send({ installed: specs.length, base: m.base.toString() });
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
          } catch (e) { send({ attachErr: sp.cls + ': ' + e }); }
      });
      send({ ready: true });
  }
  rpc.exports = { install: install, dump: function(){ return recs; } };
  setInterval(function(){ send({ snapshot: true, recs: recs }); }, 20000);
  '''.replace('SPECS_JSON', json.dumps(specs))
sc = sess.create_script(js)
state = {'recs': {}, 'ready': False}
def on_msg(msg, data):
    p = msg.get('payload')
    if not p:
        if msg.get('type') == 'error':
            print('[JS error]', msg.get('description'), flush=True)
        return
    if p.get('installed') is not None:
        print('[JS] hooks installed = %d, base = %s' % (p['installed'], p['base']), flush=True)
    if p.get('attachErr'):
        print('[JS attachErr]', p['attachErr'], flush=True)
    if p.get('ready'):
        state['ready'] = True
    if p.get('snapshot'):
        state['recs'] = p['recs']
        # 进度上报给文件，便于外部观察
        hit = [v for v in p['recs'].values() if v['calls']]
        line = time.strftime('%H:%M:%S') + '  有构造的类=' + str(len(hit)) + ' : ' + \
               (', '.join('%s=%d' % (v['cls'], v['calls']) for v in hit[:10]) or '(无)')
        print(line, flush=True)
sc.on('message', on_msg)
sc.load()
print('script loaded; resuming game ...', flush=True)
local.resume(pid)
print('resumed at ' + time.strftime('%H:%M:%S') + '  (窗口 %d s)' % DUR, flush=True)
print('>>> 现在可以操作游戏了 <<<', flush=True)
t0 = time.time()
alive = True
while time.time() - t0 < DUR:
    time.sleep(5)
    try:
        sc.exports_sync.dump()
    except Exception as e:
        alive = False
        print('!! 与目标的连接中断:', e, flush=True)
        break
print('时间到，收尾 ...', flush=True)
recs = state['recs'] or {}
if alive:
    try:
        recs = sc.exports_sync.dump() or recs
    except Exception as e:
        print('dump 失败（沿用最后一次快照）:', e, flush=True)
summary = []
for k, v in (recs or {}).items():
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
    print('  %-14s slots=%-3d calls=%-7d match=%-7d mismatch=%-6d unreadable=%-6d first=%s'
          % (x['cls'], x['slots'], x['calls'], x['match'], x['mismatch'],
             x['unreadable'], x['firstThis']), flush=True)
print('写盘:', OUT, flush=True)
# 关键：先优雅 detach，让 frida 恢复目标，再退出
try:
    sc.unload()
    print('script unloaded (Interceptor 已还原)', flush=True)
except Exception as e:
    print('unload 失败:', e, flush=True)
try:
    sess.detach()
    print('sess detached', flush=True)
except Exception as e:
    print('detach 失败:', e, flush=True)
print('done', flush=True)