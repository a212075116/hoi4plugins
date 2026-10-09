# -*- coding: utf-8 -*-
# 枚举内存区域，估算扫描成本
import frida, time, json, sys
PID = int(sys.argv[1]) if len(sys.argv) > 1 else 41224
local = frida.get_local_device()
sess = local.attach(PID)
js = '''
  var ranges = Process.enumerateRanges('rw-');
  var total = 0;
  var priv = 0, mapped = 0;
  var buckets = {};
  ranges.forEach(function(r){
      total += r.size;
      if (r.file && r.file.path) { mapped += r.size; } else { priv += r.size; }
      var key = r.protection;
      buckets[key] = (buckets[key] || 0) + r.size;
  });
  send({ count: ranges.length, totalMB: (total/1048576)|0,
         privMB: (priv/1048576)|0, mappedMB: (mapped/1048576)|0,
         buckets: buckets,
         sample: ranges.slice(0,6).map(function(r){
             return { base: r.base.toString(), size: r.size, prot: r.protection,
                      file: r.file ? r.file.path : null }; }) });
  '''
sc = sess.create_script(js)
msgs = []
sc.on('message', lambda m, d: msgs.append(m))
sc.load()
time.sleep(2)
p = msgs[0].get('payload') if msgs else None
if p:
    print('ranges =', p['count'])
    print('total  = %d MB   private = %d MB   file-mapped = %d MB'
          % (p['totalMB'], p['privMB'], p['mappedMB']))
    print('by protection:', json.dumps(p['buckets']))
    print('sample ranges:')
    for r in p['sample']:
        print('   %s  size=%-10d %s  %s' % (r['base'], r['size'], r['prot'], r['file']))
else:
    print('no payload', msgs[:1])
sess.detach()