'use strict';
rpc.exports = {
  rtti: function (vtRva) {
    const m = Process.getModuleByName('hoi4.exe');
    const out = [];
    try {
      const vt = m.base.add(vtRva);
      // vftable[-1] 在 MSVC x64 存的是指向 COL 的指针
      const colPtr = vt.sub(8).readPointer();
      out.push('vtable rva=' + vtRva.toString(16));
      out.push('  vftable[-1] = ' + colPtr);
      let col = null;
      if (!colPtr.isNull() && colPtr.compare(m.base) >= 0 && colPtr.compare(m.base.add(0x3800000)) < 0) {
        col = colPtr;
        out.push('  COL rva=' + col.sub(m.base).toString(16));
      } else {
        // 本 exe 可能是 4 字节 RVA 形式
        const r32 = vt.sub(4).readU32();
        out.push('  vftable[-4] u32=' + r32.toString(16));
        col = m.base.add(r32 >>> 0);
        out.push('  COL rva=' + (r32 >>> 0).toString(16));
      }
      const sig = col.readU32();
      const off = col.add(4).readU32();
      const cdOff = col.add(8).readU32();
      const ptd = col.add(0xc).readU32();   // x64: DWORD RVA
      const pcd = col.add(0x10).readU32();
      out.push('  signature=' + sig.toString(16) + ' offset=' + off + ' cdOffset=' + cdOff);
      out.push('  pTypeDescriptor rva=' + ptd.toString(16) + '  pClassDescriptor rva=' + pcd.toString(16));
      if (ptd !== 0) {
        const td = m.base.add(ptd >>> 0);
        const nm = td.add(0x10).readUtf8String();   // TypeDescriptor: pVFTable(8) + spare(8) + name
        out.push('  *** 类名 = ' + nm);
      }
    } catch (e) { out.push('ERR ' + e); }
    return out.join('\n');
  }
};
