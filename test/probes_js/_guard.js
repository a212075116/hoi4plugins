'use strict';
const FN = 0xf9ae60;
let calls = 0;
let armed = false;
const objs = [];
const hits = [];
const armedPages = {};
function m_() { return Process.getModuleByName('hoi4.exe'); }

Process.setExceptionHandler(function (e) {
  try {
    if (e.type === 'access-violation') {
      const page = e.address.and(ptr('0xfffffffffffff000'));
      const key = page.toString();
      if (armedPages[key]) {
        // 记录调用栈
        const bt = Thread.backtrace(e.context, Backtracer.FUZZY);
        const base = m_().base;
        const fr = [];
        for (let i = 0; i < bt.length && i < 12; i++) {
          const r = bt[i].sub(base).toInt32();
          if (r > 0 && r < 0x3800000) fr.push(bt[i].sub(base).toString(16));
        }
        if (hits.length < 20) hits.push('addr=' + e.address + ' op=' + (armedPages[key]) + ' from=' + fr.join(' <- '));
        // 恢复可写, 让游戏继续
        try { Memory.protect(page, 0x1000, 'rw-'); } catch (x) { }
        return true;
      }
    }
  } catch (x) { }
  return false;
});

function armPages() {
  if (armed) return 0;
  armed = true;
  let n = 0;
  for (let i = 0; i < objs.length && n < 8; i++) {
    try {
      const page = objs[i].and(ptr('0xfffffffffffff000'));
      const k = page.toString();
      if (armedPages[k]) continue;
      armedPages[k] = 'guard';
      Memory.protect(page, 0x1000, 'r--');
      n++;
    } catch (e) { }
  }
  return n;
}

rpc.exports = {
  install: function () {
    Interceptor.attach(m_().base.add(FN), {
      onEnter: function (args) {
        calls++;
        this.self = args[0];
        if (!armed && calls === 300) { try { armPages(); } catch (e) { } }
      },
      onLeave: function (ret) {
        try {
          const p = this.self.add(0x50);
          if (p.readS32() !== 0) objs.push(p);
        } catch (e) { }
      }
    });
    return 'hooked';
  },
  calls: function () { return calls; },
  armed: function () { return armed; },
  pages: function () { return Object.keys(armedPages).length; },
  dump: function () { return hits.length ? hits.join('\n') : '(none)'; }
};
