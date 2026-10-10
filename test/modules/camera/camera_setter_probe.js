rpc.exports = {
  dump: function () {
    var img = Process.getModuleByName('hoi4.exe').base;
    var obj = ptr(img).add(0x332F698).readPointer();
    var cam = obj.add(0x750).readPointer();
    var out = [];
    var names = {
      0x670:'', 0x674:'位置X?', 0x678:'当前高度?', 0x67C:'位置Z?',
      0x680:'B.x', 0x684:'B.y(高度副本)', 0x688:'B.z',
      0x68C:'C.x', 0x690:'C.y(小常量9.5)', 0x694:'C.z',
      0x698:'D.x', 0x69C:'D.y(目标高度)', 0x6A0:'D.z',
      0x6A4:'E.x', 0x6A8:'E.y(9.5)', 0x6AC:'E.z',
      0x6B0:'flag',
      0x6D0:'下限', 0x6D4:'上限', 0x6FC:'水平距离'
    };
    for (var off = 0x670; off <= 0x6B4; off += 4) {
      var v = cam.add(off).readFloat();
      var mark = '';
      if (isNaN(v)) mark = '  NaN!';
      var nm = names[off] || '';
      out.push('+0x' + off.toString(16) + '  ' + v.toFixed(3) + '   ' + nm + mark);
    }
    out.push('+0x6D0(下限) int = ' + cam.add(0x6D0).readInt());
    out.push('+0x6D4(上限) int = ' + cam.add(0x6D4).readInt());
    out.push('+0x6FC(水平距离) = ' + cam.add(0x6FC).readFloat().toFixed(3));
    return out.join('\n');
  },
  callSet: function (y) {
    var img = Process.getModuleByName('hoi4.exe').base;
    var obj = ptr(img).add(0x332F698).readPointer();
    var cam = obj.add(0x750).readPointer();
    var buf = Memory.alloc(16);
    buf.add(0).writeFloat(cam.add(0x698).readFloat());
    buf.add(4).writeFloat(y);
    buf.add(8).writeFloat(cam.add(0x6A0).readFloat());
    var fn = new NativeFunction(img.add(0x1262730), 'void', ['pointer','pointer']);
    fn(cam, buf);
    return 'called sub_141262730 with y=' + y;
  },
  oldSet: function (y) {
    var img = Process.getModuleByName('hoi4.exe').base;
    var obj = ptr(img).add(0x332F698).readPointer();
    var cam = obj.add(0x750).readPointer();
    var fn = new NativeFunction(img.add(0x12643F0), 'void', ['pointer','float']);
    fn(cam, y);
    return 'called sub_1412643F0 (old) with ' + y;
  }
};
