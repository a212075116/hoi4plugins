'use strict';
const FN = 0xf91850;
let n = 0;
const info = [];

function cls(vt) {
  try {
    const m = Process.getModuleByName('hoi4.exe');
    const col = vt.sub(8).readPointer();
    if (col.isNull() || col.compare(m.base) < 0 || col.compare(m.base.add(0x3800000)) >= 0) return 'vt?' + vt;
    const ptd = col.add(0xc).readU32();
    if (ptd === 0) return 'noTD';
    return m.base.add(ptd >>> 0).add(0x10).readUtf8String();
  } catch (e) { return 'ERR ' + e; }
}

rpc.exports = {
  install: function () {
    const m = Process.getModuleByName('hoi4.exe');
    Interceptor.attach(m.base.add(FN), {
      onEnter: function (args) {
        n++;
        if (info.length >= 6) return;
        try {
          const self = args[0];
          const vt = self.readPointer();
          const cnt = self.add(0x21c).readS32();
          const arr = self.add(0x210).readPointer();
          const rec = ['--- call #' + n + ' ---',
            '  this=' + self + '  class=' + cls(vt),
            '  this+0x208(byte)=' + self.add(0x208).readU8(),
            '  this+0x210 ptr=' + arr + '  this+0x21c count=' + cnt,
            '  arg2(rdx)=' + args[1]];
          if (!arr.isNull() && cnt > 0 && cnt < 100) {
            for (let i = 0; i < Math.min(cnt, 5); i++) {
              try {
                const e0 = arr.add(i * 8).readPointer();
                let c = '';
                try { c = cls(e0.readPointer()); } catch (x) { c = '?'; }
                rec.push('    [' + i + '] ' + e0 + '  class=' + c);
              } catch (x) { rec.push('    [' + i + '] 读失败'); }
            }
          }
          info.push(rec.join('\n'));
        } catch (e) { info.push('ERR ' + e); }
      }
    });
    return 'hooked ' + m.base.add(FN);
  },
  calls: function () { return n; },
  dump: function () { return info.length ? info.join('\n') : '(none)'; }
};
