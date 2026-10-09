
'use strict';
const CAM_SLOT = 0x332F698;

rpc.exports = {
  vcall: function () {
    const base = Process.getModuleByName('hoi4.exe').base;
    const L = [];
    const obj = base.add(CAM_SLOT).readPointer();
    if (obj.isNull()) return '[!] obj NULL';
    const vt = obj.readPointer();
    const fnPtr = vt.add(0x130).readPointer();

    L.push('obj          = ' + obj);
    L.push('obj->vftable = ' + vt);
    L.push('vt[0x130]    = ' + fnPtr + '  (rva 0x' + fnPtr.sub(base).toString(16) + ')');
    L.push('obj+0x750    = ' + obj.add(0x750).readPointer() + '   <- 直接读字段');

    const fn = new NativeFunction(fnPtr, 'pointer', ['pointer']);
    const ret = fn(obj);
    L.push('虚调用返回值 = ' + ret + '   <- 调用 vt[0x130](obj)');
    L.push('一致? ' + (ret.equals(obj.add(0x750).readPointer()) ? 'YES ✓' : 'NO ✗'));

    if (!ret.isNull()) {
      L.push('');
      L.push('通过虚调用拿到 cam 后读它的字段:');
      L.push('  cam+0x69C (目标高度) = ' + ret.add(0x69C).readFloat());
      L.push('  cam+0x6D0 (下限)     = ' + ret.add(0x6D0).readInt());
      L.push('  cam+0x6D4 (上限)     = ' + ret.add(0x6D4).readInt());
      L.push('  cam+0x678 (当前高度) = ' + ret.add(0x678).readFloat());
    }
    return L.join('\n');
  }
};
