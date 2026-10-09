# -*- coding: utf-8 -*-
# 扫描内存找已存在的游戏对象实例（多目标，一次遍历每目标一次扫描）
import frida, time, json, sys
PID = int(sys.argv[1])
WAIT = int(sys.argv[2]) if len(sys.argv) > 2 else 1500
OUT = sys.argv[3] if len(sys.argv) > 3 else 'reports/instance_scan.json'
# 目标：游戏逻辑类 + 已验证的活跃类
TT = json.load(open('reports/vt_list.json', encoding='utf-8'))['vt']
WANT = {'CUnit': 0x29530D8, 'CCountry': 0x27E7360, 'CState': 0x2936CC0,
        'CProvince': 0x2971B18, 'CGameDate': 0x27183A8, 'CEffect': 0x27D4990,
        'CTrigger': 0x27D55F0, 'CArmy': 0x295A2B0, 'CFleet': 0x2962A18,
        'CEventScope': 0x27D43E8, 'CCharacter': 0x297EA60}
targets = [{'cls': k, 'rva': v} for k, v in WANT.items()]
print('目标 %d 个:' % len(targets), ', '.join(t['cls'] for t in targets), flush=True)
local = frida.get_local_device()
sess = local.attach(PID)
js = '''
  var m = Process.enumerateModules().filter(function(x){
      return x.name.toLowerCase() === 'hoi4.exe'; })[0];
  var targets = TARGETS_JSON.map(function(t){
      var a = m.base.add(t.rva);
      var b = '';
      for (var i = 0; i < 8; i++) b += ('0' + a.add(i).readU8().toString(16)).slice(-2) + ' ';
      return { cls: t.cls, rva: t.rva, addr: a.toString(), pat: b.trim(),
               hits: 0, where: [] };
  });
  setTimeout(function(){
      var ranges = Process.enumerateRanges('rw-');
      var t0 = Date.now();
      var scanned = 0, errs = 0;
      for (var i = 0; i < ranges.length; i++) {
          var r = ranges[i];
          if (r.size > 64*1048576) continue;   // 跳过超大内存池，它们不含对象
          var ok = true;
          targets.forEach(function(t){
              try {
                  Memory.scanSync(r.base, r.size, t.pat).forEach(function(x){
                      t.hits++;
                      if (t.where.length < 6) t.where.push(x.address.toString());
                  });
              } catch (e) { ok = false; }
          });
          if (ok) scanned += r.size; else errs++;
          if ((i % 300) === 0) {
              send({ progress: true, done: i, total: ranges.length,
                     scannedMB: (scanned/1048576)|0, ms: Date.now()-t0,
                     hits: targets.map(function(t){ return t.cls+'='+t.hits; }).join(' ') });
          }
      }
      send({ ok: true, scannedMB: (scanned/1048576)|0, ms: Date.now()-t0, errs: errs,
             ranges: ranges.length,
             results: targets.map(function(t){
                 return { cls: t.cls, addr: t.addr, hits: t.hits, where: t.where }; }) });
  }, 50);
  '''.replace('TARGETS_JSON', json.dumps(targets))
sc = sess.create_script(js)
msgs = []
sc.on('message', lambda m, d: msgs.append(m))
sc.load()
print('scan started ...', flush=True)
t0 = time.time()
final = None
while time.time() - t0 < WAIT:
    while msgs:
        p = msgs.pop(0).get('payload', {})
        if p.get('progress'):
            print('  %4ds  %d/%d ranges  %d MB  |  %s' % (int(time.time()-t0),
                  p['done'], p['total'], p['scannedMB'], p['hits']), flush=True)
        elif p.get('ok'):
            final = p
    if final:
        break
    time.sleep(3)
if final:
    print('', flush=True)
    print('扫描完成: %d MB / %d ranges / %.0f s (errs=%d)' % (final['scannedMB'],
          final['ranges'], final['ms']/1000, final['errs']), flush=True)
    for r in final['results']:
        print('  %-14s vt=%s  hits=%d' % (r['cls'], r['addr'], r['hits']), flush=True)
        for w in r['where'][:3]:
            print('        实例候选 @', w, flush=True)
    json.dump(final, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('写盘:', OUT, flush=True)
else:
    print('未在窗口内完成，沿用进度', flush=True)
try:
    sc.unload()
except Exception:
    pass
try:
    sess.detach()
except Exception:
    pass