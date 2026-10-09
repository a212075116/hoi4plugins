'use strict';
rpc.exports = {
  base: function () { return Process.getModuleByName('hoi4.exe').base.toString(); },
  dis: function (startRva, count) {
    const m = Process.getModuleByName('hoi4.exe');
    let p = m.base.add(startRva);
    const out = [];
    for (let i = 0; i < count; i++) {
      try {
        const ins = Instruction.parse(p);
        let extra = '';
        if (ins.mnemonic === 'call' || ins.mnemonic === 'jmp') {
          const t = ins.operands[0];
          if (t && t.type === 'imm') {
            const tv = ptr(t.value);
            if (tv.compare(m.base) >= 0 && tv.compare(m.base.add(0x3800000)) < 0) {
              extra = ' -> rva=' + tv.sub(m.base).toString(16);
            } else {
              extra = ' -> ' + tv;
            }
          }
        }
        if (ins.mnemonic === 'lea' && ins.opStr.indexOf('rip') >= 0) {
          const m2 = /\[rip \+ (0x[0-9a-f]+)\]/.exec(ins.opStr);
          if (m2) {
            const target = ins.next.add(parseInt(m2[1], 16));
            if (target.compare(m.base) >= 0 && target.compare(m.base.add(0x3800000)) < 0) {
              extra = '   ; rva=' + target.sub(m.base).toString(16);
            }
          }
        }
        out.push('  ' + ins.address.sub(m.base).toString(16) + ':  ' + ins.mnemonic + ' ' + ins.opStr + extra);
        p = ins.next;
      } catch (e) { out.push('  fail @ ' + p.sub(m.base).toString(16) + ': ' + e); break; }
    }
    return out.join('\n');
  }
};
