'use strict';
const FN = 0xf9ae60;
let calls = 0;
const objs = [];
const events = [];
function m_() { return Process.getModuleByName('hoi4.exe'); }
rpc.exports = {
  install: function () {
    Interceptor.attach(m_().base.add(FN), {
      onEnter: function (args) {
        calls++;
        // 每 20 次调用扫一遍已记录对象, 看谁变 0 了
        if (calls % 20 === 0 || calls === 446) {
          let zero = 0;
          for (let i = 0; i < objs.length; i++) {
            try { if (objs[i].readS32() === 0) zero++; } catch (e) { }
          }
          events.push('第 ' + calls + ' 次调用时: 已记录 ' + objs.length + ' 个, 其中 tag==0 的有 ' + zero);
        }
        this.self = args[0];
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
  events: function () { return events.length ? events.join('\n') : '(none)'; },
  final: function () {
    let zero = 0, alive = 0;
    for (let i = 0; i < objs.length; i++) {
      try { if (objs[i].readS32() === 0) zero++; else alive++; } catch (e) { }
    }
    return 'recorded=' + objs.length + ' tag0=' + zero + ' tag!=0=' + alive;
  }
};
