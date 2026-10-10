rpc.exports = {
  all: function () {
    var img = Process.getModuleByName('hoi4.exe').base;
    var obj = ptr(img).add(0x332F698).readPointer();
    if (obj.isNull()) return 'idler NULL';
    var cam = obj.add(0x750).readPointer();
    if (cam.isNull()) return 'cam NULL';
    var groups = [
      ['A实际', 0x674],
      ['B组  ', 0x680],
      ['C组  ', 0x68C],
      ['D目标', 0x698],
      ['E终点', 0x6A4]
    ];
    var out = [];
    for (var i = 0; i < groups.length; i++) {
      var base = groups[i][1];
      var sx = cam.add(base).readFloat();
      var sy = cam.add(base + 4).readFloat();
      var sz = cam.add(base + 8).readFloat();
      var tags = '';
      if (isNaN(sx) || isNaN(sy) || isNaN(sz)) tags = '  NaN!';
      out.push(groups[i][0] + ' x=' + sx.toFixed(3) + '  y=' + sy.toFixed(3) + '  z=' + sz.toFixed(3) + tags);
    }
    out.push('---');
    out.push('+0x6B0 flag=' + cam.add(0x6B0).readU8());
    out.push('+0x6F8 flag=' + cam.add(0x6F8).readU8());
    out.push('+0x6F0 lock=' + cam.add(0x6F0).readU8());
    out.push('+0x6D0 lo=' + cam.add(0x6D0).readInt() + '  +0x6D4 hi=' + cam.add(0x6D4).readInt());
    out.push('+0x6FC dist=' + cam.add(0x6FC).readFloat().toFixed(3));
    var obj2 = obj;
    out.push('--- 对象基址 ' + cam);
    return out.join('\n');
  }
};
