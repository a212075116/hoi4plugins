
'use strict';
const CAM_SLOT = 0x332F698;
const GS_SLOT  = 0x332F260;

function u32(p) { return p.readU32(); }

rpc.exports = {
  probe: function () {
    const base = Process.getModuleByName('hoi4.exe').base;
    const L = [];
    L.push('hoi4 base = ' + base);
    L.push('CGameState slot = ' + base.add(GS_SLOT).readPointer());
    const slot = base.add(CAM_SLOT);
    const obj = slot.readPointer();
    L.push('cam slot value  = ' + obj);
    if (obj.isNull()) { L.push('[!] NULL'); return L.join('\n'); }
    const vt = obj.readPointer();
    L.push('obj->vftable    = ' + vt + '   (rva 0x' + vt.sub(base).toString(16) + ')');
    // 反查类名: vftable-8 = COL, COL+0x0C = u32 RVA to TypeDescriptor, TD+0x10 = name
    try {
      const col = vt.sub(8).readPointer();
      L.push('COL             = ' + col);
      const sig = u32(col);
      L.push('COL sig         = ' + sig);
      if (sig === 1) {
        const tdRva = u32(col.add(0x0C));
        const td = base.add(tdRva);
        const nm = td.add(0x10).readCString();
        L.push('TypeDescriptor  = ' + td + '  (rva 0x' + tdRva.toString(16) + ')');
        L.push('类名            = ' + nm);
      }
    } catch (e) { L.push('RTTI 读取失败: ' + e); }
    L.push('obj+0x750       = ' + obj.add(0x750).readPointer());
    const fn = vt.add(0x130).readPointer();
    L.push('vt[0x130]       = ' + fn + '   (rva 0x' + fn.sub(base).toString(16) + ')');
    return L.join('\n');
  }
};
