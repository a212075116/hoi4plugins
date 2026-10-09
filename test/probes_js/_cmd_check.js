
'use strict';
const MGR_RVA = 0x35E1A80;
const ENTRY   = 456;

function rstr(p, cap) {
  // 读 CString32: {union{char[16];char*} , size, cap}
  const capv = p.add(0x18).readU64().toNumber();
  const size = p.add(0x10).readU64().toNumber();
  let base;
  if (capv <= 15) base = p;                    // SSO: 缓冲就在结构开头
  else base = p.readPointer();
  if (size <= 0 || size > 200) return { s: '(空/异常)', size: size, cap: capv };
  const bytes = base.readByteArray(size);
  const u8 = new Uint8Array(bytes);
  let out = '';
  for (let i = 0; i < u8.length; i++) { if (u8[i] === 0) break; out += String.fromCharCode(u8[i]); }
  return { s: out, size: size, cap: capv };
}

rpc.exports = {
  dump: function () {
    const base = Process.getModuleByName('hoi4.exe').base;
    const mgr = base.add(MGR_RVA).readPointer();
    const data = mgr.readPointer();
    const capacity = mgr.add(8).readInt();
    const count = mgr.add(12).readInt();
    const lines = [];
    lines.push('mgr=' + mgr + '  data=' + data + '  capacity=' + capacity + '  count=' + count);
    lines.push('--- 最后 6 条命令 ---');
    const from = Math.max(0, count - 6);
    for (let i = from; i < count; i++) {
      const e = data.add(i * ENTRY);
      const flag = e.readInt();
      const name = rstr(e.add(0x08));
      const usage = rstr(e.add(0x28));
      const desc = rstr(e.add(0x48));
      const handler = e.add(0x68).readPointer();
      const argCount = e.add(0x80).readInt();
      lines.push('[' + i + '] flag=' + flag + ' name="' + name.s + '" desc="' + desc.s +
                 '" argc=' + argCount + ' handler=' + handler +
                 ' nameSize=' + name.size + ' nameCap=' + name.cap);
    }
    return lines.join('\n');
  },
  find: function (needle) {
    const base = Process.getModuleByName('hoi4.exe').base;
    const mgr = base.add(MGR_RVA).readPointer();
    const data = mgr.readPointer();
    const count = mgr.add(12).readInt();
    const hits = [];
    for (let i = 0; i < count; i++) {
      const e = data.add(i * ENTRY);
      const nm = rstr(e.add(0x08));
      if (nm.s.indexOf(needle) >= 0) {
        hits.push({ index: i, name: nm.s, handler: e.add(0x68).readPointer().toString(),
                    desc: rstr(e.add(0x48)).s, argc: e.add(0x80).readInt() });
      }
    }
    return JSON.stringify(hits, null, 1);
  }
};
