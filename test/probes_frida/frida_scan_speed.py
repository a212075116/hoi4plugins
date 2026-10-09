# -*- coding: utf-8 -*-
# 内存扫描测速：先扫一块，推算全量成本
import frida, time, json, sys
PID = int(sys.argv[1]) if len(sys.argv) > 1 else 41224
MEASURE_MB = int(sys.argv[2]) if len(sys.argv) > 2 else 64
local = frida.get_local_device()
sess = local.attach(PID)
js = '''
  var MEASURE = %d * 1048576;
  var ranges = Process.enumerateRanges('rw-');
  ranges.sort(function(a,b){ return b.size - a.size; });
  var picked = [], acc = 0;
  for (var i = 0; i < ranges.length && acc < MEASURE; i++) {
      picked.push(ranges[i]); acc += ranges[i].size;
  }
  var scanned = 0, hits = 0;
  var t0 = Date.now();
  picked.forEach(function(r){
      var size = Math.min(r.size, MEASURE - scanned);
      if (size <= 0) return;
      Memory.scanSync(r.base, size, '?? ?? ?? ?? f6 7f 00 00').forEach(function(m){
          hits++;
      });
      scanned += size;
  });
  var dt = Date.now() - t0;
  var totalRw = 0;
  ranges.forEach(function(r){ totalRw += r.size; });
  send({ scannedMB: (scanned/1048576)|0, hits: hits, ms: dt,
         mbps: (scanned/1048576) / (dt/1000),
         totalRwMB: (totalRw/1048576)|0,
         estTotalSec: (totalRw/1048576) / ((scanned/1048576) / (dt/1000)),
         largest: picked.slice(0,3).map(function(r){ return r.base.toString()+'/'+r.size; }) });
  ''' % MEASURE_MB
sc = sess.create_script(js)
msgs = []
sc.on('message', lambda m, d: msgs.append(m))
sc.load()
time.sleep(1)
p = msgs[0].get('payload') if msgs else None
if p:
    print('scanned  = %d MB' % p['scannedMB'])
    print('hits     = %d' % p['hits'])
    print('time     = %d ms' % p['ms'])
    print('speed    = %.1f MB/s' % p['mbps'])
    print('total rw = %d MB' % p['totalRwMB'])
    print('est full scan = %.1f s' % p['estTotalSec'])
    print('largest ranges:', p['largest'])
else:
    print('no payload', msgs[:1])
sess.detach()