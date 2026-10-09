'use strict';
const FN = 0xf9b050;
const all = [];
function M() { return Process.getModuleByName('hoi4.exe'); }
rpc.exports = {
  install: function () {
    Interceptor.attach(M().base.add(FN), {
      onEnter: function (args) { this.self = args[0]; },
      onLeave: function (ret) { try { all.push(this.self); } catch (e) { } }
    });
    return 'hooked';
  },
  n: function () { return all.length; },
  // 列出所有进入抵抗系统的州 id
  ids: function () {
    const out = [];
    for (let i = 0; i < all.length; i++) {
      try { out.push(all[i].add(8).readPointer().add(0x58).readS32()); } catch (e) { }
    }
    out.sort(function (a, b) { return a - b; });
    return out.join(', ');
  },
  st: function (id) {
    for (let i = 0; i < all.length; i++) {
      try {
        const r = all[i], s = r.add(8).readPointer();
        if (s.add(0x58).readS32() !== id) continue;
        return '州 ' + id + ': ctrl=' + s.add(0xc8).readS32() + ' occTag=' + r.add(0x50).readS32() + ' flag208=' + r.add(0x208).readU8();
      } catch (e) { }
    }
    return '(未找到 ' + id + ')';
  }
};
