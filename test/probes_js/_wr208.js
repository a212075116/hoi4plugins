'use strict';
const TXT_RVA = 0x1000, TXT_SIZE = 0x27050d8;
// 目标: 写 [reg+0x208] 的指令
//  C6 /0 ib   mov byte ptr [reg+disp32], imm8   -> C6 8x 08 02 00 00 xx
//  88 /r      mov byte ptr [reg+disp32], r8     -> 88 8x 08 02 00 00
//  8A 反向是读; 也扫 C6 80 08 02 00 00 (mov byte [rax+208], imm)
rpc.exports = {
  scan: function () {
    const m = Process.getModuleByName('hoi4.exe');
    const buf = m.base.add(TXT_RVA).readByteArray(TXT_SIZE);
    const u8 = new Uint8Array(buf);
    const dv = new DataView(buf);
    const out = [];
    for (let i = 0; i + 10 < u8.length; i++) {
      const op = u8[i];
      // 88 /r 或 C6 /0 : modrm 的 mod=10 (disp32) 且 rm!=100(SIB)
      if (op !== 0x88 && op !== 0xc6) continue;
      const modrm = u8[i + 1];
      const mod = modrm >> 6, reg = (modrm >> 3) & 7, rm = modrm & 7;
      if (mod !== 2) continue;
      if (rm === 4) continue;           // SIB, 跳过
      const disp = dv.getInt32(i + 2, true);
      if (disp !== 0x208) continue;
      const lo = Math.max(0, i - 24);
      let ctx = '';
      for (let k = lo; k < i; k++) ctx += ('0' + u8[k].toString(16)).slice(-2) + ' ';
      out.push({ rva: TXT_RVA + i, op: op.toString(16), modrm: modrm.toString(16), ctx: ctx, reg: reg });
      if (out.length > 60) break;
    }
    return out.map(function (x) {
      return 'rva=' + x.rva.toString(16) + '  op=' + x.op + ' modrm=' + x.modrm + '  ...' + x.ctx;
    }).join('\n') || '(none)';
  }
};
