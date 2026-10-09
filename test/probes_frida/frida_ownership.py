# -*- coding: utf-8 -*-
# 归属验证修正版：在 onLeave（构造完成后）读 [this]，才是真正的归属证据
import frida, time, json, sys
EXE = r'D:\SteamLibrary\steamapps\common\Hearts of Iron IV\hoi4.exe'
CWD = r'D:\SteamLibrary\steamapps\common\Hearts of Iron IV'
DUR = int(sys.argv[1]) if len(sys.argv) > 1 else 900
OUT = sys.argv[2] if len(sys.argv) > 2 else 'reports/live_objects5.json'
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
print('specs = %d，窗口 %d s' % (len(specs), DUR), flush=True)
local = frida.get_local_device()
pid = local.spawn([EXE], cwd=CWD)
print('pid =', pid, flush=True)
sess = local.attach(pid)
js = '''
  var specs = SPECS_JSON;
  var recs = {};
  var VTNAME = VTNAME_JSON;   // 运行时虚表地址 -> 类名，用于识别 mismatch 到底指向谁
  function install() {
      var m = Process.enumerateModules().filter(function(x){
          return x.name.toLowerCase() === 'hoi4.exe'; })[0];
      if (!m) return 'no module';
      var ok = 0, fail = 0;
      specs.forEach(function(sp){
          var key = sp.cls + '|' + sp.rva;
          var r = recs[key] || (recs[key] = {
              cls: sp.cls, rva: sp.rva, n: sp.n, ctors: [],
              calls: 0, enterZero: 0, leaveMatch: 0, leaveMismatch: 0,
              unreadable: 0, firstThis: null, firstEnter: null, firstLeave: null,
              leaveOther: {} });
          if (r.ctors.indexOf(sp.ctor) < 0) r.ctors.push(sp.ctor);
          var fnAddr = m.base.add(sp.ctor - 0x140000000);
          var vtAddr = m.base.add(sp.rva);
          try {
              Interceptor.attach(fnAddr, {
                  onEnter: function(args) {
                      r.calls++;
                      this.t = args[0];
                      if (this.t.isNull()) { r.enterZero++; return; }
                      var v;
                      try { v = this.t.readPointer(); } catch (e) { r.unreadable++; return; }
                      if (r.firstEnter === null) r.firstEnter = v.toString();
                      if (v.isNull()) r.enterZero++;
                  },
                  onLeave: function(retval) {
                      var t = this.t;
                      if (!t || t.isNull()) return;
                      var v;
                      try { v = t.readPointer(); } catch (e) { return; }
                      if (r.firstThis === null) r.firstThis = t.toString();
                      if (r.firstLeave === null) r.firstLeave = v.toString();
                      if (v.equals(vtAddr)) r.leaveMatch++;
                      else {
                          r.leaveMismatch++;
                          var k = v.toString();
                          var nm = VTNAME[k] || k;
                          r.leaveOther[nm] = (r.leaveOther[nm] || 0) + 1;
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
  '''.replace('SPECS_JSON', json.dumps(specs)) \
     .replace('VTNAME_JSON', json.dumps({}))
sc = sess.create_script(js)
def summarize(recs):
    out = []
    for k, v in recs.items():
        out.append(dict(v))
    out.sort(key=lambda x: -x['calls'])
    return out
def on_msg(msg, data):
    p = msg.get('payload')
    if not p:
        if msg.get('type') == 'error':
            print('[JS error]', msg.get('description'), flush=True)
        return
    if p.get('installed') is not None:
        print('[JS] installed=%d failed=%d base=%s' % (p['installed'], p['failed'], p['base']), flush=True)
    if p.get('snapshot'):
        sm = summarize(p['recs'])
        json.dump(sm, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('', flush=True)
        print('=== ' + time.strftime('%H:%M:%S') + ' ===', flush=True)
        for x in sm:
            if x['calls']:
                tot = x['leaveMatch'] + x['leaveMismatch']
                pct = ('%.1f%%' % (100.0*x['leaveMatch']/tot)) if tot else '-'
                print('  %-13s calls=%-7d enterZero=%-7d | onLeave: match=%-7d mismatch=%-7d 归属=%s'
                      % (x['cls'], x['calls'], x['enterZero'], x['leaveMatch'],
                         x['leaveMismatch'], pct), flush=True)
                if x['leaveMismatch'] and x['leaveOther']:
                    top = sorted(x['leaveOther'].items(), key=lambda kv: -kv[1])[:3]
                    print('        实际指向: ' + ', '.join('%s x%d' % (a, b) for a, b in top), flush=True)
sc.on('message', on_msg)
sc.load()
res = sc.exports_sync.install()
print('install() ->', res, flush=True)
local.resume(pid)
print('>>> hook 已就位（onEnter + onLeave 双读）<<<', flush=True)
t0 = time.time()
while time.time() - t0 < DUR:
    time.sleep(5)
    try:
        sc.exports_sync.dump()
    except Exception as e:
        print('!! 连接中断:', e, flush=True)
        break
try:
    recs = sc.exports_sync.dump()
    json.dump(summarize(recs), open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('最终落盘:', OUT, flush=True)
except Exception:
    pass
try:
    sc.unload(); print('unloaded', flush=True)
except Exception:
    pass
try:
    sess.detach(); print('detached', flush=True)
except Exception:
    pass