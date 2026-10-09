# -*- coding: utf-8 -*-
# 按「单个候选函数」分别统计 onLeave 的 match/mismatch，判定该函数是构造还是析构
import frida, time, json, sys
EXE = r'D:\SteamLibrary\steamapps\common\Hearts of Iron IV\hoi4.exe'
CWD = r'D:\SteamLibrary\steamapps\common\Hearts of Iron IV'
DUR = int(sys.argv[1]) if len(sys.argv) > 1 else 600
OUT = sys.argv[2] if len(sys.argv) > 2 else 'reports/per_func.json'
T = json.load(open('reports/ctor_targets.json', encoding='utf-8'))
WANT = ['CGameState','CCountry','CState','CProvince','CCharacter','CUnit','CArmy','CFleet',
        'CEffect','CTrigger','CDecision']
specs, seen = [], set()
for x in T:
    if x['cls'] not in WANT or x['cls'] == 'CModifier':
        continue
    key = (x['cls'], x['ctor'], x['rva'])
    if key in seen:
        continue
    seen.add(key)
    specs.append({'cls': x['cls'], 'rva': x['rva'], 'n': x['n'], 'ctor': x['ctor']})
print('specs = %d（按 函数 维度）' % len(specs), flush=True)
local = frida.get_local_device()
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
          var key = sp.cls + '@0x' + sp.ctor.toString(16) + '|vt' + sp.rva.toString(16);
          var r = recs[key] || (recs[key] = {
              cls: sp.cls, ctor: sp.ctor, rva: sp.rva, n: sp.n,
              calls: 0, enterZero: 0, leaveMatch: 0, leaveMismatch: 0,
              firstLeave: null, leaveOther: {} });
          var fnAddr = m.base.add(sp.ctor - 0x140000000);
          var vtAddr = m.base.add(sp.rva);
          try {
              Interceptor.attach(fnAddr, {
                  onEnter: function(args) {
                      r.calls++;
                      this.t = args[0];
                      if (this.t.isNull()) { r.enterZero++; return; }
                      try { if (this.t.readPointer().isNull()) r.enterZero++; } catch (e) {}
                  },
                  onLeave: function(retval) {
                      var t = this.t;
                      if (!t || t.isNull()) return;
                      var v;
                      try { v = t.readPointer(); } catch (e) { return; }
                      if (r.firstLeave === null) r.firstLeave = v.toString();
                      if (v.equals(vtAddr)) r.leaveMatch++;
                      else {
                          r.leaveMismatch++;
                          var k = v.toString();
                          r.leaveOther[k] = (r.leaveOther[k] || 0) + 1;
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
  setInterval(function(){ send({ snapshot: true, recs: recs }); }, 30000);
  '''.replace('SPECS_JSON', json.dumps(specs))
sc = sess.create_script(js)
def on_msg(msg, data):
    p = msg.get('payload')
    if not p:
        if msg.get('type') == 'error':
            print('[JS error]', msg.get('description'), flush=True)
        return
    if p.get('installed') is not None:
        print('[JS] installed=%d failed=%d' % (p['installed'], p['failed']), flush=True)
    if p.get('snapshot'):
        rows = sorted(p['recs'].values(), key=lambda x: (x['cls'], x['ctor']))
        json.dump(rows, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('', flush=True)
        print('=== ' + time.strftime('%H:%M:%S') + '  按函数维度 ===', flush=True)
        print('%-13s %-12s %-9s %-9s %-9s %-9s %s' % ('类', '构造函数', 'calls', 'enter零', 'match', 'mismatch', '判定'), flush=True)
        for x in rows:
            if not x['calls']: continue
            tot = x['leaveMatch'] + x['leaveMismatch']
            pct = (100.0*x['leaveMatch']/tot) if tot else 0
            verdict = '构造(完整对象)' if pct > 80 else ('析构/基类子对象' if pct < 20 else '混合')
            print('%-13s 0x%-9X %-9d %-9d %-9d %-9d %s (%.0f%%)'
                  % (x['cls'], x['ctor'], x['calls'], x['enterZero'], x['leaveMatch'],
                     x['leaveMismatch'], verdict, pct), flush=True)
            for k, v in sorted(x['leaveOther'].items(), key=lambda kv: -kv[1])[:2]:
                print('        [this] -> %s x%d' % (k, v), flush=True)
sc.on('message', on_msg)
sc.load()
sc.exports_sync.install()
local.resume(pid)
print('>>> hook 已就位 <<<', flush=True)
t0 = time.time()
while time.time() - t0 < DUR:
    time.sleep(5)
    try:
        sc.exports_sync.dump()
    except Exception as e:
        print('!! 中断:', e, flush=True)
        break
try:
    rows = sorted(sc.exports_sync.dump().values(), key=lambda x: (x['cls'], x['ctor']))
    json.dump(rows, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('最终落盘:', OUT, flush=True)
except Exception:
    pass
try:
    sc.unload(); print('unloaded', flush=True)
except Exception: pass
try:
    sess.detach(); print('detached', flush=True)
except Exception: pass