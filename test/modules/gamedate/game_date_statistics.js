'use strict';
function M() { return Process.getModuleByName('hoi4.exe'); }
const TARGETS = [
  { rva: 0x24BDB80, tag: 'getU32' },
  { rva: 0x24BBFF0, tag: 'getB' },
  { rva: 0x24BF5B0, tag: 'fmt227' },
  { rva: 0x24BF960, tag: 'short9a' },
  { rva: 0x24BFBA0, tag: 'short9b' }
];
const cnt = {};
const vals = {};
for (let i = 0; i < TARGETS.length; i++) { cnt[TARGETS[i].tag] = 0; vals[TARGETS[i].tag] = {}; }
rpc.exports = {
  ready: function () { return M().base.toString(); },
  install: function () {
    const out = [];
    for (let i = 0; i < TARGETS.length; i++) {
      const t = TARGETS[i];
      try {
        Interceptor.attach(M().base.add(t.rva), {
          onLeave: function (ret) {
            try {
              cnt[t.tag]++;
              const v = ret.toInt32();
              if (Math.abs(v) < 1000000) vals[t.tag][v] = (vals[t.tag][v] || 0) + 1;
            } catch (e) { }
          }
        });
        out.push(t.tag + '=ok');
      } catch (e) { out.push(t.tag + '=ERR'); }
    }
    return out.join(' ');
  },
  stat: function () {
    const out = [];
    for (let i = 0; i < TARGETS.length; i++) {
      const t = TARGETS[i].tag;
      const ks = Object.keys(vals[t]).slice(0, 6).map(function (k) { return k + 'x' + vals[t][k]; });
      out.push(t + ': ' + cnt[t] + ' 次  值[' + ks.join(' ') + ']');
    }
    return out.join('\n');
  }
};
