'use strict';
const FN = 0xf9ae60;
let calls = 0, tagZero = 0;
const tagVals = {};
function m_() { return Process.getModuleByName('hoi4.exe'); }
rpc.exports = {
  install: function () {
    Interceptor.attach(m_().base.add(FN), {
      onEnter: function (args) {
        calls++;
        try {
          const tag = args[0].add(0x50).readS32();
          if (tag === 0) tagZero++;
          else tagVals[String(tag)] = (tagVals[String(tag)] || 0) + 1;
        } catch (e) { }
      }
    });
    return 'hooked ' + m_().base.add(FN);
  },
  stats: function () {
    const ks = Object.keys(tagVals).length;
    return 'calls=' + calls + '  tag0=' + tagZero + '  不同tag数=' + ks;
  },
  tags: function () {
    const a = [];
    for (const k in tagVals) a.push(k + ':' + tagVals[k]);
    return a.slice(0, 30).join(' ');
  }
};
