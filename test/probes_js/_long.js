'use strict';
const FN1 = 0xf9ae60;   // UpdateOccupation
const FN2 = 0xf9b050;   // 设置 tag 与 flag
let n1 = 0, n2 = 0;
const time1 = [];
const time2 = [];
function m_() { return Process.getModuleByName('hoi4.exe'); }
rpc.exports = {
  install: function () {
    Interceptor.attach(m_().base.add(FN1), {
      onEnter: function () { n1++; if (time1.length < 20 && n1 <= 3) time1.push(Date.now()); }
    });
    Interceptor.attach(m_().base.add(FN2), {
      onEnter: function () { n2++; if (time2.length < 20 && n2 <= 3) time2.push(Date.now()); }
    });
    return 'hooked';
  },
  stats: function () { return 'UpdateOccupation=' + n1 + '  SetTagAndFlag=' + n2; }
};
