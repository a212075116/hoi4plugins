'use strict';
const FN = 0xf9ae60;
let calls = 0;
let armed = false;
const objs = [];
const hits = [];
function m_() { return Process.getModuleByName('hoi4.exe'); }

function armAll() {
  if (armed) return;
  armed = true;
  const base = m_().base;
  const seenPages = {};
  let n = 0;
  for (let i = 0; i < objs.length && n < 24; i++) {
    try {
      const target = objs[i];
      const page = target.and(ptr('0xfffffffffffff000')).toString();
      if (seenPages[page]) continue;
      seenPages[page] = 1;
      n++;
      const t = target;
      MemoryAccessMonitor.enable({ base: ptr(page), size: 0x1000 }, {
        onAccess: function (d) {
          try {
            if (d.operation !== 'write') return;
            const off = d.address.sub(t);
            const o = off.toInt32();
            if (o < 0x50 || o >= 0x54) return;
            const bt = Thread.backtrace(d.context, Backtracer.FUZZY);
            const fr = [];
            for (let k = 0; k < bt.length && k < 10; k++) {
              const r = bt[k].sub(base).toInt32();
              if (r > 0 && r < 0x3800000) fr.push(bt[k].sub(base).toString(16));
            }
            if (hits.length < 30) hits.push('obj=' + t + ' 写入后 val=' + d.address.readS32() + '  from=' + fr.join(' <- '));
          } catch (e) { }
        }
      });
    } catch (e) { }
  }
  return n;
}

rpc.exports = {
  install: function () {
    Interceptor.attach(m_().base.add(FN), {
      onEnter: function (args) { calls++; this.self = args[0]; },
      onLeave: function (ret) {
        try {
          const p = this.self.add(0x50);
          if (p.readS32() !== 0) objs.push(p);
        } catch (e) { }
        // 第 446 次 (或 >= 440) 调用结束时立即装监控
        if (!armed && calls >= 440) {
          try { armAll(); } catch (e) { }
        }
      }
    });
    return 'hooked';
  },
  calls: function () { return calls; },
  armed: function () { return armed; },
  state: function () {
    let zero = 0, alive = 0;
    for (let i = 0; i < objs.length; i++) {
      try { if (objs[i].readS32() === 0) zero++; else alive++; } catch (e) { }
    }
    return 'recorded=' + objs.length + ' tag0=' + zero + ' tag!=0=' + alive;
  },
  dump: function () { return hits.length ? hits.join('\n') : '(none)'; }
};
