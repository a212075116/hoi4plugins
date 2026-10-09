'use strict';
const FN = 0xf9b050;
let calls = 0;
const res = [];
const ev = [];
function m_() { return Process.getModuleByName('hoi4.exe'); }
function countZero() {
  let z = 0;
  for (let i = 0; i < res.length; i++) { try { if (res[i].add(0x50).readS32() === 0) z++; } catch (e) { } }
  return z;
}
rpc.exports = {
  install: function () {
    Interceptor.attach(m_().base.add(FN), {
      onEnter: function (args) { calls++; this.self = args[0]; },
      onLeave: function (ret) {
        try {
          const s = this.self;
          const tag = s.add(0x50).readS32();
          if (tag !== 0) res.push(s);
          // 每次出口都检查前面对象有没有变 0
          const z = countZero();
          if (z > 0 && ev.length < 15) {
            ev.push('第 ' + calls + ' 次出口时: 已记录 ' + res.length + ' 个, 其中 tag==0 的有 ' + z + ' (本次对象 tag=' + tag + ')');
          }
        } catch (e) { }
      }
    });
    return 'hooked';
  },
  calls: function () { return calls; },
  ev: function () { return ev.length ? ev.join('\n') : '(无)'; },
  final: function () { return 'recorded=' + res.length + ' tag0=' + countZero(); }
};
