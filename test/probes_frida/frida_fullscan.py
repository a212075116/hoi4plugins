# -*- coding: utf-8 -*-
# 全量扫描内存，统计多个虚表的实例指针分布
import frida, time, json, sys
PID = int(sys.argv[1]) if len(sys.argv) > 1 else 41224
WAIT = int(sys.argv[2]) if len(sys.argv) > 2 else 900
TARGETS = [
    ('CGui',        0x2B3F4E0),
    ('CButtonWrapper', 0x294C180),
    ('CButtonObserverGlue', 0x273AA38),
    ('CEffect',     0x27D4990),
    ('CUnit',       0x29530D8),
    ('CPdxMouse',   0x2B59550),
]
local = frida.get_local_device()
sess = local.attach(PID)
js = '''
  var m = Process.enumerateModules().filter(function(x){
      return x.name.toLowerCase() === 'hoi4.exe'; })[0];
  var targets = TARGETS_JSON.map(function(t){
      var a = m.base.add(t.rva);
      var b = '';
      for (var i = 0; i < 8; i++) b += ('0' + a.add(i).readU8().toString(16)).slice(-2) + ' ';
      return { cls: t.cls, addr: a.toString(), pat: b.trim(), hits: 0, where: [] };
  });
  setTimeout(function(){
      var ranges = Process.enumerateRanges('rw-');
      var t0 = Date.now();
      var scanned = 0, errs = 0;
      for (var i = 0; i < ranges.length; i++) {
          var r = ranges[i];
          var buf;
          try { buf = r.base.readByteArray(r.size); } catch (e) { errs++; continue; }
          if (!buf) { errs++; continue; }
          scanned += r.size;
          targets.forEach(function(t){
              try {
                  Memory.scanSync(r.base, r.size, t.pat).forEach(function(x){
                      t.hits++;
                      if (t.where.length < 8) t.where.push(x.address.toString());
                  });
              } catch (e) {}
          });
          if ((i % 200) === 0) {
              send({ progress: true, done: i, total: ranges.length,
                     scannedMB: (scanned/1048576)|0, ms: Date.now()-t0,
                     hits: targets.map(function(t){ return t.cls + '=' + t.hits; }).join(' ') });
          }
      }
      var dt = Date.now() - t0;
      send({ ok: true, scannedMB: (scanned/1048576)|0, ms: dt, errs: errs,
             ranges: ranges.length,
             results: targets.map(function(t){
                 return { cls: t.cls, addr: t.addr, hits: t.hits, where: t.where }; }) });
  }, 50);
  '''.replace('TARGETS_JSON', json.dumps([{'cls': a, 'rva': b} for a, b in TARGETS]))
sc = sess.create_script(js)
msgs = []
sc.on('message', lambda m, d: msgs.append(m))
sc.load()
print('scan started ...')
deadline = time.time() + WAIT
last = None
while time.time() < deadline:
    while msgs:
        p = msgs.pop(0).get('payload', {})
        if p.get('progress'):
            print('  progress %d/%d  %d MB  %d ms  %s' % (p['done'], p['total'],
                  p['scannedMB'], p['ms'], p['hits']))
        elif p.get('ok'):
            last = p
    if last:
        break
    time.sleep(3)
if last:
    print('')
    print('scanned %d MB over %d ranges in %.0f s (errs=%d)'
          % (last['scannedMB'], last['ranges'], last['ms']/1000, last['errs']))
    for r in last['results']:
        print('  %-22s vt=%s  hits=%d' % (r['cls'], r['addr'], r['hits']))
        for w in r['where'][:4]:
            print('        at', w)
else:
    print('did not finish within wait window')
sess.detach()