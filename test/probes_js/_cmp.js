
'use strict';
const CAM_SLOT = 0x332F698;
const RVA_SETTER = 0x12643F0;

function cam() {
  const base = Process.getModuleByName('hoi4.exe').base;
  const obj = base.add(CAM_SLOT).readPointer();
  if (obj.isNull()) return null;
  const c = obj.add(0x750).readPointer();
  return c.isNull() ? null : c;
}

rpc.exports = {
  snap: function () {
    const c = cam();
    if (!c) return 'cam NULL';
    return '+0x69C(目标)=' + c.add(0x69C).readFloat().toFixed(2) +
           '  +0x678(当前)=' + c.add(0x678).readFloat().toFixed(2) +
           '  +0x698=' + c.add(0x698).readFloat().toFixed(2) +
           '  +0x6A0=' + c.add(0x6A0).readFloat().toFixed(2);
  },

  // 方式A: 直接写 +0x69C
  directWrite: function (h) {
    const c = cam();
    if (!c) return 'cam NULL';
    const b = c.add(0x69C).readFloat();
    c.add(0x69C).writeFloat(h);
    return '直接写: +0x69C ' + b.toFixed(2) + ' -> ' + c.add(0x69C).readFloat().toFixed(2);
  },

  // 方式B: 调用 setter
  callSetter: function (h) {
    const c = cam();
    if (!c) return 'cam NULL';
    const base = Process.getModuleByName('hoi4.exe').base;
    const b = c.add(0x69C).readFloat();
    const b698 = c.add(0x698).readFloat();
    new NativeFunction(base.add(RVA_SETTER), 'void', ['pointer', 'float'])(c, h);
    return '调 setter: +0x69C ' + b.toFixed(2) + ' -> ' + c.add(0x69C).readFloat().toFixed(2) +
           '   +0x698 ' + b698.toFixed(2) + ' -> ' + c.add(0x698).readFloat().toFixed(2);
  },

  // 跟踪: 每 200ms 采一次, 共 n 次
  track: function (n) {
    const out = [];
    const c = cam();
    if (!c) return 'cam NULL';
    for (let i = 0; i < n; i++) {
      out.push('  t=' + (i * 200) + 'ms  +0x69C=' + c.add(0x69C).readFloat().toFixed(2) +
               '  +0x678=' + c.add(0x678).readFloat().toFixed(2) +
               '  +0x698=' + c.add(0x698).readFloat().toFixed(2));
      if (i + 1 < n) {
        const t = Date.now();
        while (Date.now() - t < 200) {}
      }
    }
    return out.join('\n');
  }
};
