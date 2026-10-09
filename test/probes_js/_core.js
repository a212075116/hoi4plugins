'use strict';
const FN = 0xf9b050;
let calls = 0;
const res = [];
function M() { return Process.getModuleByName('hoi4.exe'); }
rpc.exports = {
  install: function () {
    Interceptor.attach(M().base.add(FN), {
      onEnter: function (args) { calls++; this.self = args[0]; },
      onLeave: function (ret) {
        try { res.push(this.self); } catch (e) { }
      }
    });
    return 'hooked';
  },
  calls: function () { return calls; },
  // 统计核心区(有 core) vs 非核心区 的 tag / flag208
  core: function () {
    let coreN = 0, coreFlag1 = 0, coreTagNZ = 0, nonN = 0, nonFlag1 = 0, nonTagNZ = 0;
    const list = [];
    for (let i = 0; i < res.length; i++) {
      try {
        const r = res[i];
        const st = r.add(8).readPointer();
        const id = st.add(0x58).readS32();
        const cnt = st.add(0xbc).readS32();
        const tag = r.add(0x50).readS32();
        const flag = r.add(0x208).readU8();
        if (cnt > 0) { coreN++; if (flag) coreFlag1++; if (tag !== 0) coreTagNZ++; }
        else { nonN++; if (flag) nonFlag1++; if (tag !== 0) nonTagNZ++; }
        if (list.length < 12) list.push('id=' + id + ' core=' + cnt + ' tag=' + tag + ' flag208=' + flag);
      } catch (e) { }
    }
    return '核心区(core>0): ' + coreN + ' 个, 其中 flag208=1 的 ' + coreFlag1 + ', tag!=0 的 ' + coreTagNZ +
      '\n非核心(core=0): ' + nonN + ' 个, 其中 flag208=1 的 ' + nonFlag1 + ', tag!=0 的 ' + nonTagNZ +
      '\n前 12 个样本:\n  ' + list.join('\n  ');
  }
};
