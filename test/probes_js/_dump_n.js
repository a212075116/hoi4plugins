
'use strict';
const MGR_RVA = 0x35E1A80;
const ENTRY   = 456;
function cstr(p) {
  const cap = p.add(0x18).readU64().toNumber();
  const size = p.add(0x10).readU64().toNumber();
  let base = (cap <= 15) ? p : p.readPointer();
  if (size <= 0 || size > 300) return null;
  const u8 = new Uint8Array(base.readByteArray(size));
  let out = '';
  for (let i = 0; i < u8.length; i++) { if (u8[i] === 0) break; out += String.fromCharCode(u8[i]); }
  return out;
}
rpc.exports = {
  dumpN: function (want) {
    const base = Process.getModuleByName('hoi4.exe').base;
    const mgr = base.add(MGR_RVA).readPointer();
    const data = mgr.readPointer();
    const count = mgr.add(12).readInt();
    const L = [];
    let shown = 0;
    for (let i = 0; i < count && shown < 3; i++) {
      const e = data.add(i * ENTRY);
      const v28 = e.add(0x28).readInt();
      if (v28 !== want) continue;
      shown++;
      const nm = cstr(e.add(0x08));
      L.push('entry [' + i + '] "' + nm + '"  +0x28=' + v28);
      for (const off of [0x28, 0x30, 0x38, 0x40, 0x48, 0x68, 0x70, 0x78, 0x80, 0x88, 0xA8, 0xC8, 0xE8]) {
        const q = e.add(off).readU64().toString();
        let note = '';
        try { const s = cstr(e.add(off)); if (s !== null) note = ' CStr="' + s + '"'; } catch (x) {}
        if (!note) {
          try { const p = e.add(off).readPointer(); if (!p.isNull()) { const s = p.readCString(); if (s !== null) note = ' ->"' + s.slice(0,30) + '"'; } } catch (x) {}
        }
        L.push('   +0x' + off.toString(16).toUpperCase().padStart(3,'0') + ' q=0x' + BigInt(q).toString(16).padStart(16,'0') + note);
      }
      L.push('');
    }
    return L.join('\n');
  }
};
