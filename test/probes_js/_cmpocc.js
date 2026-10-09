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
        try { if (this.self.add(0x50).readS32() !== 0) res.push(this.self); } catch (e) { }
      }
    });
    return 'hooked';
  },
  calls: function () { return calls; },
  cmp: function () {
    const keep = [], zero = [];
    for (let i = 0; i < res.length; i++) {
      try {
        const r = res[i];
        const st = r.add(8).readPointer();
        const id = st.add(0x58).readS32();
        (r.add(0x50).readS32() !== 0 ? keep : zero).push([id, r, st]);
      } catch (e) { }
    }
    const out = [];
    out.push('保持=' + keep.length + '  变0=' + zero.length);
    const pick = function (arr, tag) {
      if (!arr.length) return;
      for (let k = 0; k < Math.min(arr.length, 2); k++) {
        const e = arr[k], r = e[1], st = e[2];
        out.push('--- ' + tag + ' id=' + e[0] + ' ---');
        out.push('  CState+0xc8(owner)=' + st.add(0xc8).readS32() + '  +0xcc=' + st.add(0xcc).readS32());
        const cnt = st.add(0xbc).readS32(), a2 = st.add(0xb0).readPointer();
        let vals = [];
        for (let i = 0; i < Math.min(cnt, 6); i++) { try { vals.push(a2.add(i * 4).readS32()); } catch (x) { } }
        out.push('  core count=' + cnt + ' 列表=' + vals.join(','));
        out.push('  tag=' + r.add(0x50).readS32() + '  flag208=' + r.add(0x208).readU8());
        out.push('  res+0x10=' + r.add(0x10).readS32() + '  +0x14=' + r.add(0x14).readS32() + '  +0x18=' + r.add(0x18).readS32());
      }
    };
    pick(keep, '保持 tag');
    pick(zero, '变 0');
    return out.join('\n');
  }
};
