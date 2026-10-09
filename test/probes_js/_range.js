
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
    const c = cam(); if (!c) return 'cam NULL';
    return '+0x69C=' + c.add(0x69C).readFloat().toFixed(2) +
           '  +0x684=' + c.add(0x684).readFloat().toFixed(2) +
           '  +0x6D0=' + c.add(0x6D0).readInt() + '  +0x6D4=' + c.add(0x6D4).readInt();
  },
  setR: function (h) {
    const c = cam(); if (!c) return 'cam NULL';
    new NativeFunction(Process.getModuleByName('hoi4.exe').base.add(RVA_SETTER), 'void', ['pointer', 'float'])(c, h);
    return 'setter(' + h + ') -> +0x69C=' + c.add(0x69C).readFloat().toFixed(2);
  },
  writeR: function (h) {
    const c = cam(); if (!c) return 'cam NULL';
    c.add(0x69C).writeFloat(h);
    return 'write(' + h + ') -> +0x69C=' + c.add(0x69C).readFloat().toFixed(2);
  },
  settle: function (ms) {
    const c = cam(); if (!c) return 'cam NULL';
    const t = Date.now();
    while (Date.now() - t < ms) {}
    return '  等 ' + ms + 'ms 后: +0x69C=' + c.add(0x69C).readFloat().toFixed(2) +
           '  +0x678=' + c.add(0x678).readFloat().toFixed(2);
  }
};
