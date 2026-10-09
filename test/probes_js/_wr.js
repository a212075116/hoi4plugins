'use strict';
const WR = 0xf9b46e;   // mov byte ptr [rbp+0x208], al
let n = 0;
const recs = [];
const seenTag = {};
function m_() { return Process.getModuleByName('hoi4.exe'); }
rpc.exports = {
  install: function () {
    Interceptor.attach(m_().base.add(WR), {
      onEnter: function () {
        try {
          const ctx = this.context;
          const self = ctx.rbp;
          const tag = self.add(0x50).readS32();
          const al = (ctx.rax.toInt32() & 0xff);
          n++;
          const key = tag + '|' + al;
          seenTag[key] = (seenTag[key] || 0) + 1;
          if (recs.length < 8) {
            recs.push('#' + n + '  self=' + self + '  tag=' + tag + '  al=' + al);
          }
        } catch (e) { }
      }
    });
    return 'hooked ' + m_().base.add(WR);
  },
  stats: function () {
    const a = [];
    for (const k in seenTag) a.push(k + ' x' + seenTag[k]);
    return 'total=' + n + '\n  ' + a.slice(0, 20).join('\n  ');
  },
  dump: function () { return recs.join('\n'); }
};
