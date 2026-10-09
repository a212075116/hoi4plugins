'use strict';
const FN = 0xf9b050;
let calls = 0;
const res = [];
function m_() { return Process.getModuleByName('hoi4.exe'); }
rpc.exports = {
  install: function () {
    Interceptor.attach(m_().base.add(FN), {
      onEnter: function (args) { calls++; this.self = args[0]; },
      onLeave: function (ret) {
        try {
          const s = this.self;
          if (s.add(0x50).readS32() !== 0) res.push(s);
        } catch (e) { }
      }
    });
    return 'hooked ' + m_().base.add(FN);
  },
  calls: function () { return calls; },
  // 读出保持 tag 的州 id (CState+0x58, 与 0xf9adb0 打日志用的字段一致)
  report: function () {
    const keep = [], zero = [];
    for (let i = 0; i < res.length; i++) {
      try {
        const r = res[i];
        const tag = r.add(0x50).readS32();
        const st = r.add(8).readPointer();
        const id = st.add(0x58).readS32();
        if (tag !== 0) keep.push(id); else zero.push(id);
      } catch (e) { }
    }
    return '总数=' + res.length +
      '\n保持 tag 的州 (' + keep.length + '): ' + keep.join(', ') +
      '\n变 0 的州 (' + zero.length + '): ' + zero.slice(0, 40).join(', ') + (zero.length > 40 ? ' ...' : '');
  }
};
