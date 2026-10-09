
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
  find: function (name) {
    const base = Process.getModuleByName('hoi4.exe').base;
    const mgr = base.add(MGR_RVA).readPointer();
    const data = mgr.readPointer();
    const count = mgr.add(12).readInt();
    for (let i = 0; i < count; i++) {
      const e = data.add(i * ENTRY);
      if (cstr(e.add(0x08)) === name) return e;
    }
    return null;
  },

  // dump 一个 entry 的 [from, to) 原始 8 字节一格
  dumpEntry: function (name, from, to) {
    const e = this.find(name);
    if (e === null) return '未找到 ' + name;
    const L = [];
    L.push('entry "' + name + '" @ ' + e);
    for (let off = from; off < to; off += 8) {
      const q = e.add(off).readU64().toString();
      const d0 = e.add(off).readU32();
      const d1 = e.add(off + 4).readU32();
      // 尝试当作 CString 解析
      let asStr = '';
      try { const s = cstr(e.add(off)); if (s !== null) asStr = '  asCStr="' + s + '"'; } catch (x) {}
      L.push('  +0x' + off.toString(16).toUpperCase().padStart(3, '0') +
             '  q=0x' + BigInt(q).toString(16).padStart(16, '0') +
             '  u32=[' + d0 + ', ' + d1 + ']' + asStr);
    }
    return L.join('\n');
  },

  // 直接把某个 offset 当 int 读, 看补全函数会循环多少次
  argCountGuess: function (name) {
    const e = this.find(name);
    if (e === null) return '未找到';
    const v28 = e.add(0x28).readInt();
    const L = [];
    L.push('entry "' + name + '"');
    L.push('  *(int*)(+0x28) = ' + v28 + '   <-- 补全函数把它当循环次数');
    L.push('  *(int*)(+0x40) = ' + e.add(0x40).readInt());
    L.push('  *(int*)(+0x80) = ' + e.add(0x80).readInt() + '   <-- 我们以为的 argc');
    const p30 = e.add(0x30).readPointer();
    L.push('  *(void**)(+0x30) = ' + p30 + '   <-- 补全函数从这里读 char*');
    try { L.push('     该指针指向: "' + p30.readCString() + '"'); } catch (x) { L.push('     该指针无法读取: ' + x); }
    const p68 = e.add(0x68).readPointer();
    L.push('  *(void**)(+0x68) = ' + p68 + '   <-- 我们以为的 handler');
    return L.join('\n');
  }
};
