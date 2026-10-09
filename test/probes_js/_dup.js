'use strict';
const FN = 0xf9b050;
let calls = 0;
const seen = {};
const dups = [];
let zeroIn = 0;
function m_() { return Process.getModuleByName('hoi4.exe'); }
rpc.exports = {
  install: function () {
    Interceptor.attach(m_().base.add(FN), {
      onEnter: function (args) {
        calls++;
        try {
          const s = args[0];
          const k = s.toString();
          const tagIn = s.add(0x50).readS32();
          if (tagIn === 0) zeroIn++;
          if (seen[k] === undefined) {
            seen[k] = { n: 1, firstTag: tagIn };
          } else {
            seen[k].n++;
            if (dups.length < 20) dups.push('对象 ' + k + ' 第 ' + seen[k].n + ' 次进入, 进入时 tag=' + tagIn + ' (首次 tag=' + seen[k].firstTag + ')');
          }
        } catch (e) { }
      }
    });
    return 'hooked ' + m_().base.add(FN);
  },
  stats: function () {
    let multi = 0;
    for (const k in seen) if (seen[k].n > 1) multi++;
    return 'calls=' + calls + '  不同对象=' + Object.keys(seen).length + '  被多次调用的=' + multi + '  进入时tag=0的次数=' + zeroIn;
  },
  dups: function () { return dups.length ? dups.join('\n') : '(无重复)'; }
};
