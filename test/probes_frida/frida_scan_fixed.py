# -*- coding: utf-8 -*-
# 固定字节模式搜索虚表指针（异步执行，避免 load 超时）
import frida, time, json, sys
PID = int(sys.argv[1]) if len(sys.argv) > 1 else 41224
MEASURE_MB = int(sys.argv[2]) if len(sys.argv) > 2 else 512
WAIT = int(sys.argv[3]) if len(sys.argv) > 3 else 180
RVA = 0x2B3F4E0   # ??_7CGui@@6B@ (静态 0x142B3F4E0, imagebase 0x140000000)
local = frida.get_local_device()
sess = local.attach(PID)
js = '''
  var MEASURE = %d * 1048576;
  var RVA = %d;
  var m = Process.enumerateModules().filter(function(x){
      return x.name.toLowerCase() === 'hoi4.exe'; })[0];
  var target = m.base.add(RVA);
  var bytes = '';
  for (var i = 0; i < 8; i++) { bytes += ('0' + target.add(i).readU8().toString(16)).slice(-2) + ' '; }
  bytes = bytes.trim();
  setTimeout(function(){
      var ranges = Process.enumerateRanges('rw-');
      ranges.sort(function(a,b){ return b.size - a.size; });
      var picked = [], acc = 0;
      for (var i = 0; i < ranges.length && acc < MEASURE; i++) {
          picked.push(ranges[i]); acc += ranges[i].size;
      }
      var scanned = 0, hits = 0, where = [];
      var t0 = Date.now();
      picked.forEach(function(r){
          var size = Math.min(r.size, MEASURE - scanned);
          if (size <= 0) return;
          try {
              Memory.scanSync(r.base, size, bytes).forEach(function(x){
                  hits++;
                  if (where.length < 20) where.push(x.address.toString());
              });
          } catch (e) {}
          scanned += size;
      });
      var dt = Date.now() - t0;
      var totalRw = 0; ranges.forEach(function(r){ totalRw += r.size; });
      send({ ok: true, pattern: bytes, target: target.toString(),
             scannedMB: (scanned/1048576)|0, hits: hits, where: where, ms: dt,
             mbps: (scanned/1048576)/(dt/1000),
             totalRwMB: (totalRw/1048576)|0,
             estTotalSec: (totalRw/1048576)/((scanned/1048576)/(dt/1000)) });
  }, 50);
  ''' % (MEASURE_MB, RVA)
sc = sess.create_script(js)
msgs = []
sc.on('message', lambda m, d: msgs.append(m))
sc.load()
print('script loaded, scanning %d MB ...' % MEASURE_MB)
deadline = time.time() + WAIT
p = None
while time.time() < deadline:
    if msgs:
        p = msgs[0].get('payload')
        if p and p.get('ok'):
            break
    time.sleep(2)
if p and p.get('ok'):
    print('target  =', p['target'])
    print('pattern =', p['pattern'])
    print('scanned = %d MB in %d ms  => %.1f MB/s' % (p['scannedMB'], p['ms'], p['mbps']))
    print('est full = %.0f s (total rw %d MB)' % (p['estTotalSec'], p['totalRwMB']))
    print('HITS =', p['hits'])
    for h in p['where']:
        print('   hit at', h)
else:
    print('no result yet; latest msg:', json.dumps(msgs[:1], ensure_ascii=False)[:400])
sess.detach()