# -*- coding: utf-8 -*-
# 精确找对象（修正：按实际栈区域大小读取，不能硬编码 4MB）
import frida, time, json, sys
PID = int(sys.argv[1])
local = frida.get_local_device()
sess = local.attach(PID)
js = '''
  setTimeout(function(){
    var m = Process.enumerateModules().filter(function(x){
        return x.name.toLowerCase() === 'hoi4.exe'; })[0];
    var RVAS = RVAS_JSON;
    var vtMap = {};
    RVAS.forEach(function(r){ vtMap[m.base.add(r.rva).toString()] = r.cls; });
    var objects = {};
    var threadCount = 0, cand = 0, readable = 0, fails = 0, totalBytes = 0;
    var threads = Process.enumerateThreads();
    threads.forEach(function(t){
        var lo = null, size = 0;
        try {
            var rng = Process.findRangeByAddress(t.context.sp);
            if (rng) { lo = rng.base; size = rng.size; }
        } catch (e) { return; }
        if (!lo || size <= 0) return;
        threadCount++;
        var buf;
        try { buf = lo.readByteArray(size); } catch (e) { fails++; return; }
        if (!buf) { fails++; return; }
        totalBytes += buf.byteLength;
        var dv = new DataView(buf);
        var n = Math.floor(dv.byteLength / 8);
        for (var i = 0; i < n; i++) {
            var lob = dv.getUint32(i*8, true);
            var hib = dv.getUint32(i*8+4, true);
            if (hib > 0x10000) continue;
            if (lob < 0x10000 && hib === 0) continue;
            var p;
            try { p = ptr(hib * 4294967296 + lob); } catch (e) { continue; }
            cand++;
            var rg = null;
            try { rg = Process.findRangeByAddress(p); } catch (e) {}
            if (!rg || rg.protection.indexOf('w') < 0) continue;
            var v;
            try { v = p.readPointer(); } catch (e) { continue; }
            readable++;
            var cls = vtMap[v.toString()];
            if (cls) {
                var o = objects[cls] || (objects[cls] = { count: 0, samples: [] });
                o.count++;
                if (o.samples.length < 5) o.samples.push(p.toString());
            }
        }
    });
    send({ threads: threadCount, cand: cand, readable: readable, fails: fails,
           totalMB: (totalBytes/1048576)|0, objects: objects,
           vtCount: Object.keys(vtMap).length, base: m.base.toString() });
  }, 50);
  '''.replace('RVAS_JSON', json.dumps([
      {'cls': x['cls'], 'rva': x['rva']} for x in json.load(
          open('reports/vt_list.json', encoding='utf-8'))['vt']]))
sc = sess.create_script(js)
msgs = []
sc.on('message', lambda m, d: msgs.append(m))
sc.load()
print('loaded, waiting ...', flush=True)
t0 = time.time()
p = None
while time.time() - t0 < 100:
    if msgs:
        mm = msgs[0]
        if mm.get('type') == 'error':
            print('JS error:', mm.get('description'), flush=True)
            break
        p = mm.get('payload')
        if p:
            break
    time.sleep(2)
if p:
    print('threads=%d(成功读 %d)  vtMap=%d  读入 %.1f MB  fails=%d'
          % (p['threads'], p['threads'] - p['fails'], p['vtCount'], p['totalMB'], p['fails']), flush=True)
    print('候选指针=%d  可读=%d' % (p['cand'], p['readable']), flush=True)
    print('', flush=True)
    print('=== 栈上找到的活对象 ===', flush=True)
    objs = sorted(p['objects'].items(), key=lambda kv: -kv[1]['count'])
    for cls, o in objs[:50]:
        print('  x%-4d %-64s  @%s' % (o['count'], cls[:64], o['samples'][0]), flush=True)
    print('', flush=True)
    print('不同类数 =', len(objs), flush=True)
else:
    print('no payload', flush=True)
try:
    sc.unload()
except Exception:
    pass
try:
    sess.detach()
except Exception:
    pass