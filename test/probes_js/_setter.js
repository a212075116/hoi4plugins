
'use strict';
const CAM_SLOT = 0x332F698;
const RVA_SETTER = 0x12643F0;   // sub_1412643F0(cam, float h)

rpc.exports = {
  info: function () {
    const base = Process.getModuleByName('hoi4.exe').base;
    const obj = base.add(CAM_SLOT).readPointer();
    if (obj.isNull()) return 'idler NULL';
    const cam = obj.add(0x750).readPointer();
    if (cam.isNull()) return 'cam NULL (未进地图?)';
    const L = [];
    L.push('idler = ' + obj);
    L.push('cam   = ' + cam);
    L.push('cam+0x69C (目标高度) = ' + cam.add(0x69C).readFloat());
    L.push('cam+0x678 (当前高度) = ' + cam.add(0x678).readFloat());
    L.push('cam+0x698           = ' + cam.add(0x698).readFloat());
    L.push('cam+0x6A0           = ' + cam.add(0x6A0).readFloat());
    L.push('cam+0x6D0 (下限)     = ' + cam.add(0x6D0).readInt());
    L.push('cam+0x6D4 (上限)     = ' + cam.add(0x6D4).readInt());
    const setter = base.add(RVA_SETTER);
    L.push('setter = ' + setter + ' (rva 0x' + RVA_SETTER.toString(16) + ')');
    return L.join('\n');
  },

  // 调用 setter 设置高度
  setHeight: function (h) {
    const base = Process.getModuleByName('hoi4.exe').base;
    const obj = base.add(CAM_SLOT).readPointer();
    if (obj.isNull()) return 'idler NULL';
    const cam = obj.add(0x750).readPointer();
    if (cam.isNull()) return 'cam NULL';
    const before69C = cam.add(0x69C).readFloat();
    const before698 = cam.add(0x698).readFloat();
    const before678 = cam.add(0x678).readFloat();
    const fn = new NativeFunction(base.add(RVA_SETTER), 'void', ['pointer', 'float']);
    fn(cam, h);
    const after69C = cam.add(0x69C).readFloat();
    const after698 = cam.add(0x698).readFloat();
    return [
      '调用 sub_1412643F0(cam, ' + h + ')',
      '  +0x69C  之前=' + before69C + '  之后=' + after69C,
      '  +0x698  之前=' + before698 + '  之后=' + after698,
      '  +0x678  之前=' + before678 + ' (这个是游戏自己平滑的)',
    ].join('\n');
  },

  readHeights: function () {
    const base = Process.getModuleByName('hoi4.exe').base;
    const obj = base.add(CAM_SLOT).readPointer();
    if (obj.isNull()) return 'idler NULL';
    const cam = obj.add(0x750).readPointer();
    if (cam.isNull()) return 'cam NULL';
    return '+0x69C=' + cam.add(0x69C).readFloat() +
           '  +0x678=' + cam.add(0x678).readFloat() +
           '  +0x698=' + cam.add(0x698).readFloat();
  }
};
