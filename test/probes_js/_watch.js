'use strict';
const FN = 0xf9ae60;
let target = null;
let calls = 0;
const hits = [];
function m_() { return Process.getModuleByName('hoi4.exe'); }
rpc.exports = {
  install: function () {
    Interceptor.attach(m_().base.add(FN), {
      onEnter: function (args) { calls++; this.self = args[0]; },
      onLeave: function (ret) {
        if (target !== null) return;
        try {
          if (this.self.add(0x50).readS32() !== 0) {
            target = this.self;
          }
        } catch (e) { }
      }
    });
    return 'hooked';
  },
  calls: function () { return calls; },
  // 开始监控目标对象所在页的写入
  watch: function () {
    if (target === null) return 'no target yet';
    const m = m_();
    const pageStart = target.and(ptr('0xfffffffffffff000'));
    const base = m.base;
    MemoryAccessMonitor.enable({ base: pageStart, size: 0x1000 }, {
      onAccess: function (details) {
        try {
          const a = details.address;
          if (details.operation === 'write') {
            const off = a.sub(target);
            if (off.toInt32() >= 0x50 && off.toInt32() < 0x54) {
              const bt = Thread.backtrace(details.context, Backtracer.FUZZY);
              const lines = [];
              for (let i = 0; i < bt.length && i < 8; i++) {
                const r = bt[i].sub(base);
                if (r.toInt32() >= 0 && r.toInt32() < 0x3800000) lines.push(r.toString(16));
              }
              if (hits.length < 20) hits.push('write off=' + off + '  val=' + a.readS32() + '  from=' + lines.join(' <- '));
            }
          }
        } catch (e) { }
      }
    });
    return 'watching page ' + pageStart + ' target=' + target;
  },
  targetTag: function () { return target === null ? 'none' : String(target.add(0x50).readS32()); },
  dump: function () { return hits.length ? hits.join('\n') : '(none)'; }
};
