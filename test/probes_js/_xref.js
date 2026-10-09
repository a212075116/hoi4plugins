'use strict';
const TXT_RVA = 0x1000, TXT_SIZE = 0x27050d8;
const T = [0x297e518, 0x297e530, 0x297e560, 0x297e588, 0x297e5b0, 0x297e4f0, 0x297e4c8];
const NAME = {0x297e518:'SCALED_LAW_MODIFIER',0x297e530:'called GetOccupationLaw',0x297e560:'_OccupiedCountryTag.IsValid',0x297e588:'_State.IsCore',0x297e5b0:'IsDynamic',0x297e4f0:'Occupation data should not be null',0x297e4c8:'Garrison data should not be null'};
rpc.exports = {
  scan: function () {
    const m = Process.getModuleByName('hoi4.exe');
    const buf = m.base.add(TXT_RVA).readByteArray(TXT_SIZE);
    const u8 = new Uint8Array(buf);
    const dv = new DataView(buf);
    const out = [];
    for (let i = 4; i + 4 <= u8.length; i++) {
      const disp = dv.getInt32(i, true);
      const tgt = (TXT_RVA + i + 4 + disp) >>> 0;
      if (T.indexOf(tgt) < 0) continue;
      const lo = Math.max(0, i - 8);
      let ctx = '';
      for (let k = lo; k < i; k++) ctx += ('0' + u8[k].toString(16)).slice(-2) + ' ';
      out.push('rva=' + (TXT_RVA + i - 3).toString(16) + '  ' + ctx + ' -> ' + NAME[tgt]);
      if (out.length > 80) break;
    }
    return out.length ? out.join('\n') : '(none)';
  }
};
