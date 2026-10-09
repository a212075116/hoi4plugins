'use strict';
const FN = 0xf9b4b0;
let total = 0, active = 0, zero = 0;
const seen = {};
const sample = [];
function m_() { return Process.getModuleByName('hoi4.exe'); }
rpc.exports = {
  install: function () {
    Interceptor.attach(m_().base.add(FN), {
      onEnter: function (args) { this.res = args[0]; },
      onLeave: function (ret) {
        total++;
        if (ret.toInt32() === 0) return;
        active++;
        try {
          const r = this.res;
          const tag = r.add(0x50).readU32();
          if (tag !== 0) return;
          zero++;
          const key = String(r);
          if (!seen[key]) {
            seen[key] = 1;
            if (sample.length < 20) {
              const st = r.sub(0x268);
              sample.push('CState=' + st + '  CResistance=' + r + '  res+0x208=' + r.add(0x208).readU8());
            }
          } else {
            seen[key]++;
          }
        } catch (e) { }
      }
    });
    return 'hooked';
  },
  stats: function () { return 'total=' + total + ' active=' + active + ' tag0_active=' + zero; },
  uniq: function () { return Object.keys(seen).length; },
  dump: function () { return sample.length ? sample.join('\n') : '(none)'; }
};
