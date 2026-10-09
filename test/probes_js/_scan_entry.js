
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
  // 统计全部命令的 +0x28 与 +0x30, 以及各偏移处能否解析出 CString
  scan: function () {
    const base = Process.getModuleByName('hoi4.exe').base;
    const mgr = base.add(MGR_RVA).readPointer();
    const data = mgr.readPointer();
    const count = mgr.add(12).readInt();
    const stat28 = {};
    let nonZero28 = 0;
    const offsCStr = {};
    // 对每个偏移, 统计能解析出非空 CString 的条目数
    const probeOffs = [];
    for (let o = 0; o < 0xC8; o += 8) probeOffs.push(o);

    const samples = [];
    for (let i = 0; i < count; i++) {
      const e = data.add(i * ENTRY);
      const v28 = e.add(0x28).readInt();
      stat28[v28] = (stat28[v28] || 0) + 1;
      if (v28 !== 0) { nonZero28++; if (samples.length < 6) samples.push({ i: i, name: cstr(e.add(0x08)), v28: v28 }); }
    }
    const lines = [];
    lines.push('命令总数 = ' + count);
    lines.push('*(int*)(+0x28) != 0 的条目数 = ' + nonZero28);
    lines.push('*(int*)(+0x28) 的取值分布 (前 10):');
    const ent = Object.entries(stat28).sort((a, b) => b[1] - a[1]).slice(0, 10);
    for (const kv of ent) lines.push('   值 ' + kv[0] + ' : ' + kv[1] + ' 条');
    if (samples.length) {
      lines.push('非零样例:');
      for (const s of samples) lines.push('   [' + s.i + '] "' + s.name + '"  +0x28=' + s.v28);
    }
    lines.push('');
    lines.push('=== 各偏移作为 CString 能解析出内容的条目数 (判断字段归属) ===');
    for (const o of probeOffs) {
      let n = 0, empty = 0, bad = 0, sumLen = 0;
      const ex = [];
      for (let i = 0; i < count; i++) {
        const e = data.add(i * ENTRY);
        try {
          const s = cstr(e.add(o));
          if (s === null) { bad++; continue; }
          if (s.length === 0) { empty++; } else { n++; sumLen += s.length; if (ex.length < 2) ex.push(s); }
        } catch (x) { bad++; }
      }
      lines.push('  +0x' + o.toString(16).toUpperCase().padStart(3, '0') +
                 '  非空=' + n + '  空=' + empty + '  解析失败=' + bad +
                 (n ? '  例: ' + ex.map(x => '"' + x.slice(0, 24) + '"').join(' ') : ''));
    }
    return lines.join('\n');
  }
};
