# -*- coding: utf-8 -*-
# 扫描线程栈，找指向 vftable 的指针 —— 反映此刻活跃的对象
import frida, time, json, sys
PID = int(sys.argv[1]) if len(sys.argv) > 1 else 41224
# 关键类的 vftable RVA（来自 reports/vt_list.json，imagebase 0x140000000）
TARGETS = json.load(open('reports/vt_list.json', encoding='utf-8'))['vt']
local = frida.get_local_device()
sess = local.attach(PID)
js = '''
  var m = Process.enumerateModules().filter(function(x){
      return x.name.toLowerCase() === 'hoi4.exe'; })[0];
  var rdataLo = 0x2707000, rdataHi = 0x3085000;   // .rdata RVA 范围
  var found = {};
  var scannedBytes = 0, ptrs = 0;
  var threads = Process.enumerateThreads();
  var stackInfo = [];
  threads.forEach(function(t){
      var lo = null, hi = null;
      try {
          var ctx = t.context;
          // 用 rsp 往上找，粗略界定栈范围
          var sp = ctx.sp;
          lo = sp; hi = sp.add(3 * 1048576);
      } catch (e) { return; }
      var st = null;
      try { st = Process.findRangeByAddress(lo); } catch (e) {}
      if (st) { lo = st.base; hi = st.base.add(st.size); }
      stackInfo.push({ tid: t.id, lo: lo.toString(), hi: hi.toString(),
                       size: (hi.sub(lo).toInt32()) });
      try {
          var base = lo, size = hi.sub(lo).toInt32();
          var buf = base.readByteArray(Math.min(size, 8*1048576));
          if (buf) {
              scannedBytes += Math.min(size, 8*1048576);
              var dv = new DataView(buf);
              var n = Math.floor(dv.byteLength / 8);
              for (var i = 0; i < n; i++) {
                  var lob = dv.getUint32(i*8, true);
                  var hib = dv.getUint32(i*8+4, true);
                  // 判断是否形如 0x00007ff6_xxxxxxxx
                  if (hib !== 0x00007ff6) continue;
                  var rva = lob - (m.base.toInt32() >>> 0);
                  if (rva < rdataLo || rva >= rdataHi) continue;
                  ptrs++;
                  var key = rva.toString(16);
                  found[key] = (found[key] || 0) + 1;
              }
          }
      } catch (e) {}
  });
  send({ threads: threads.length, scannedBytes: scannedBytes, ptrs: ptrs,
         stacks: stackInfo.slice(0,8), found: found });
  '''
sc = sess.create_script(js)
msgs = []
sc.on('message', lambda m, d: msgs.append(m))
sc.load()
time.sleep(4)
p = msgs[0].get('payload') if msgs else None
if p:
    print('threads = %d   scanned = %.1f MB   rdata-range ptrs = %d'
          % (p['threads'], p['scannedBytes']/1048576, p['ptrs']))
    for st in p['stacks']:
        print('   tid=%-6d stack %s - %s  (%d bytes)' % (st['tid'], st['lo'], st['hi'], st['size']))
    # 映射 RVA -> 类名
    byRva = {('0x%X' % x['rva']).lower(): x for x in TARGETS}
    items = sorted(p['found'].items(), key=lambda kv: -kv[1])
    print('')
    print('--- 命中的虚表（RVA -> 类名）---')
    hit_known = 0
    for rva, cnt in items[:40]:
        info = byRva.get('0x' + rva)
        if info:
            hit_known += 1
            print('   x%-4d rva=0x%-10s %-60s slots=%d' % (cnt, rva.upper(), info['cls'][:60], info['n']))
        else:
            print('   x%-4d rva=0x%-10s <不在 vftable 表中>' % (cnt, rva.upper()))
    print('')
    print('总命中虚表数 = %d，其中能对上类名的 = %d' % (len(items), hit_known))
else:
    print('no payload', msgs[:2])
sess.detach()