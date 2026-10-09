'use strict';
// 目标字符串 rva=0x297e530 'called GetOccupationLaw...'
// 扫描 .rdata/.data 里指向 0x297e510..0x297e590 范围内任何地址的 8 字节指针
const LO = 0x297e510, HI = 0x297e590;
rpc.exports = {
  scan: function () {
    const m = Process.getModuleByName('hoi4.exe');
    const out = [];
    const secs = [['rdata', 0x2707000, 0x97db0c], ['data', 0x3085000, 0x562e2c]];
    for (let s = 0; s < secs.length; s++) {
      const nm = secs[s][0], rva = secs[s][1], size = secs[s][2];
      let buf;
      try { buf = m.base.add(rva).readByteArray(size); } catch (e) { continue; }
      const u8 = new Uint8Array(buf);
      const dv = new DataView(buf);
      for (let i = 0; i + 8 <= u8.length; i++) {
        const lo32 = dv.getUint32(i, true);
        const hi32 = dv.getUint32(i + 4, true);
        if (hi32 !== 0x00000001) continue;      // 0x1_xxxxxxxx
        if (lo32 < 0x20000000 || lo32 > 0x40000000) continue;
        const targetRva = lo32 - 0x40000000 + 0x40000000; // placeholder
        if (lo32 >= LO && lo32 <= HI) {
          out.push(nm + ' @rva=' + (rva + i).toString(16) + ' -> 0x1' + lo32.toString(16));
        }
      }
      if (out.length > 40) break;
    }
    return out.length ? out.join('\n') : '(none)';
  }
};
