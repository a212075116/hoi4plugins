rpc.exports = {
  dump: function () {
    var img = Process.getModuleByName('hoi4.exe').base;
    var obj = ptr(img).add(0x332F698).readPointer();
    if (obj.isNull()) return 'no idler';
    var cam = obj.add(0x750).readPointer();
    if (cam.isNull()) return 'no cam';
    var out = [];
    function f(off, name) {
      var v = cam.add(off).readFloat();
      var tag = '';
      if (isNaN(v)) tag = '   <==== NaN !!';
      else if (!isFinite(v)) tag = '   <==== Inf !!';
      out.push(name + ' = ' + v + tag);
    }
    function i(off, name) { out.push(name + ' = ' + cam.add(off).readInt()); }
    f(0x69C, 'targetHeight(+69C)');
    f(0x678, 'curHeight  (+678)');
    f(0x684, 'copyHeight (+684)');
    f(0x6FC, 'horizDist  (+6FC)');
    f(0x690, 'const9.5   (+690)');
    i(0x6D0, 'lowerLimit (+6D0)');
    i(0x6D4, 'upperLimit (+6D4)');
    return out.join('\n');
  },
  nanScan: function () {
    var img = Process.getModuleByName('hoi4.exe').base;
    var obj = ptr(img).add(0x332F698).readPointer();
    var cam = obj.add(0x750).readPointer();
    var out = [];
    for (var off = 0x660; off < 0x720; off += 4) {
      var v = cam.add(off).readFloat();
      if (isNaN(v) || !isFinite(v)) out.push('+' + off.toString(16) + ' = ' + v);
    }
    return out.length ? out.join('\n') : '(0x660~0x720 区间无 NaN/Inf)';
  }
};
