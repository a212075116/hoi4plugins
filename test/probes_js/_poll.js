'use strict';
const FN = 0xf9ae60;
const list = [];
let calls = 0;
function m_() { return Process.getModuleByName('hoi4.exe'); }
rpc.exports = {
  install: function () {
    Interceptor.attach(m_().base.add(FN), {
      onEnter: function (args) { calls++; this.self = args[0]; },
      onLeave: function (ret) {
        try {
          const s = this.self;
          const tag = s.add(0x50).readS32();
          if (tag !== 0) list.push({ addr: s.toString(), tag: tag });
        } catch (e) { }
      }
    });
    return 'hooked';
  },
  calls: function () { return calls; },
  // 统计当前有多少个 tag 变成 0 了
  poll: function () {
    let zero = 0, alive = 0, total = 0;
    const zeros = [];
    for (let i = 0; i < list.length; i++) {
      total++;
      try {
        const tag = ptr(list[i].addr).add(0x50).readS32();
        if (tag === 0) { zero++; if (zeros.length < 5) zeros.push(list[i].addr + '(was ' + list[i].tag + ')'); }
        else alive++;
      } catch (e) { }
    }
    return 'recorded=' + total + '  tag!=0=' + alive + '  tag==0=' + zero + (zeros.length ? '  例如 ' + zeros.join(', ') : '');
  },
  reset: function () { list.length = 0; return 'cleared'; }
};
