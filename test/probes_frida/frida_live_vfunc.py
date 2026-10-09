# -*- coding: utf-8 -*-
# 对栈扫描发现的活跃对象，hook 其虚表全部槽位，统计真实调用
import frida, time, json, sys
PID = int(sys.argv[1]) if len(sys.argv) > 1 else 41224
RUN = int(sys.argv[2]) if len(sys.argv) > 2 else 25
# 从 vt_list.json 里挑活跃对象（RVA 来自栈扫描命中）
VT = json.load(open('reports/vt_list.json', encoding='utf-8'))['vt']
WANT = {
    0x2B93ED0: 'CFile',
    0x2B49820: 'CBitmap',
    0x2B500B8: 'SVectorParamReader',
    0x27172D8: 'CTbbThreadObserver',
    0x2718108: 'CPdxHybridInlineBufferAllocator',
}
picked = [x for x in VT if x['rva'] in WANT]
print('picked %d vftables' % len(picked))
local = frida.get_local_device()
sess = local.attach(PID)
js = '''
  var m = Process.enumerateModules().filter(function(x){
      return x.name.toLowerCase() === 'hoi4.exe'; })[0];
  var specs = SPECS_JSON;
  var out = [];
  specs.forEach(function(sp){
      var vt = m.base.add(sp.rva);
      var rec = { cls: sp.cls, rva: sp.rva, slots: [] };
      for (var k = 0; k < sp.n; k++) {
          var fn = null;
          try { fn = vt.add(k*8).readPointer(); } catch (e) { break; }
          var ent = { k: k, fn: fn.toString(), calls: 0, err: null };
          rec.slots.push(ent);
          (function(ent){
              try {
                  Interceptor.attach(ptr(ent.fn), {
                      onEnter: function(){ ent.calls++; }
                  });
              } catch (e) { ent.err = String(e); }
          })(ent);
      }
      out.push(rec);
  });
  setTimeout(function(){ send({ recs: out }); }, RUN_MS);
  '''.replace('SPECS_JSON', json.dumps([
      {'cls': WANT[x['rva']], 'rva': x['rva'], 'n': x['n']} for x in picked])) \
     .replace('RUN_MS', str(RUN*1000))
sc = sess.create_script(js)
msgs = []
sc.on('message', lambda m, d: msgs.append(m))
sc.load()
print('hooked; observing %d s ...' % RUN)
time.sleep(RUN + 5)
p = msgs[0].get('payload') if msgs else None
byRva = {x['rva']: x for x in VT}
if p:
    tot_calls = 0
    for r in p['recs']:
        calls = sum(s2['calls'] for s2 in r['slots'])
        tot_calls += calls
        if calls == 0:
            print('')
            print('%-28s rva=0x%-8X 槽位=%d  调用=0' % (r['cls'], r['rva'], len(r['slots'])))
            continue
        print('')
        print('%-28s rva=0x%-8X 槽位=%d  总调用=%d' % (r['cls'], r['rva'], len(r['slots']), calls))
        for s2 in r['slots']:
            if s2['calls'] or s2['err']:
                print('    slot[%2d] %-18s calls=%-8d %s' % (s2['k'], s2['fn'], s2['calls'], s2['err'] or ''))
    print('')
    print('全部槽位调用合计 = %d' % tot_calls)
else:
    print('no payload', msgs[:2])
sess.detach()