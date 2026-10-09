'use strict';
const FN = 0xf9ae60;
let calls = 0;
const recs = [];
function m_() { return Process.getModuleByName('hoi4.exe'); }
function cls(vt) {
  try {
    const m = m_();
    const col = vt.sub(8).readPointer();
    if (col.isNull() || col.compare(m.base) < 0 || col.compare(m.base.add(0x3800000)) >= 0) return null;
    const ptd = col.add(0xc).readU32();
    if (ptd === 0) return null;
    return m.base.add(ptd >>> 0).add(0x10).readUtf8String();
  } catch (e) { return null; }
}
rpc.exports = {
  install: function () {
    Interceptor.attach(m_().base.add(FN), {
      onEnter: function (args) {
        calls++;
        this.self = args[0];
        this.before = args[0].add(0x50).readS32();
        this.before208 = args[0].add(0x208).readU8();
        try { this.klass = cls(args[0].readPointer()); } catch (e) { this.klass = null; }
      },
      onLeave: function (ret) {
        if (recs.length >= 5) return;
        try {
          const s = this.self;
          recs.push('#' + calls + '  class=' + this.klass +
            '\n   入口: tag=' + this.before + '  flag208=' + this.before208 +
            '\n   出口: tag=' + s.add(0x50).readS32() + '  flag208=' + s.add(0x208).readU8() +
            '\n   ret=' + ret);
        } catch (e) { recs.push('ERR ' + e); }
      }
    });
    return 'hooked';
  },
  calls: function () { return calls; },
  dump: function () { return recs.join('\n'); }
};
