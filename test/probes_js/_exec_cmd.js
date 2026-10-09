
'use strict';
const MGR_RVA = 0x35E1A80;
const ENTRY   = 456;

function rstr(p) {
  const capv = p.add(0x18).readU64().toNumber();
  const size = p.add(0x10).readU64().toNumber();
  let base = (capv <= 15) ? p : p.readPointer();
  if (size <= 0 || size > 300) return '';
  const u8 = new Uint8Array(base.readByteArray(size));
  let out = '';
  for (let i = 0; i < u8.length; i++) { if (u8[i] === 0) break; out += String.fromCharCode(u8[i]); }
  return out;
}

// 写一个 CString32: {union{char[16];char*}, size_t size, size_t cap}
function wstr(p, s) {
  const bytes = [];
  for (let i = 0; i < s.length; i++) bytes.push(s.charCodeAt(i) & 0xff);
  const n = bytes.length;
  if (n <= 15) {
    // SSO
    for (let i = 0; i < 16; i++) p.add(i).writeU8(i < n ? bytes[i] : 0);
    p.add(0x10).writeU64(n);
    p.add(0x18).writeU64(15);
  } else {
    const buf = Memory.alloc(n + 1);
    for (let i = 0; i < n; i++) buf.add(i).writeU8(bytes[i]);
    buf.add(n).writeU8(0);
    p.writePointer(buf);
    p.add(0x10).writeU64(n);
    p.add(0x18).writeU64(n);
  }
}

rpc.exports = {
  findHandler: function (name) {
    const base = Process.getModuleByName('hoi4.exe').base;
    const mgr = base.add(MGR_RVA).readPointer();
    const data = mgr.readPointer();
    const count = mgr.add(12).readInt();
    for (let i = 0; i < count; i++) {
      const e = data.add(i * ENTRY);
      if (rstr(e.add(0x08)) === name) {
        return { index: i, handler: e.add(0x68).readPointer(), argc: e.add(0x80).readInt() };
      }
    }
    return null;
  },

  // args: 字符串数组
  exec: function (name, args) {
    const base = Process.getModuleByName('hoi4.exe').base;
    const mgr = base.add(MGR_RVA).readPointer();
    const data = mgr.readPointer();
    const count = mgr.add(12).readInt();
    let entry = null, idx = -1;
    for (let i = 0; i < count; i++) {
      const e = data.add(i * ENTRY);
      if (rstr(e.add(0x08)) === name) { entry = e; idx = i; break; }
    }
    if (!entry) return '命令未找到: ' + name;
    const handler = entry.add(0x68).readPointer();
    const argc = entry.add(0x80).readInt();

    const n = args.length;
    const strArr = Memory.alloc(32 * Math.max(n, 1));
    for (let i = 0; i < n; i++) wstr(strArr.add(i * 32), args[i]);

    // CmdArgs: { CmdString* data, int capacity, int count }  -- 16 字节
    const cmdArgs = Memory.alloc(0x20);
    cmdArgs.writePointer(strArr);
    cmdArgs.add(8).writeInt(Math.max(n, 1));
    cmdArgs.add(12).writeInt(n);

    // CmdResult: { int ok, ...; CString message @+0x08 }
    const res = Memory.alloc(0x60);
    for (let i = 0; i < 0x60; i++) res.add(i).writeU8(0);

    const fn = new NativeFunction(handler, 'pointer', ['pointer', 'pointer']);
    let err = null;
    try { fn(res, cmdArgs); } catch (e) { err = String(e); }

    const lines = [];
    lines.push('命令 "' + name + '" 槽[' + idx + '] argc=' + argc + ' handler=' + handler);
    lines.push('  传入参数: [' + args.join(', ') + ']');
    lines.push('  out->ok     = ' + res.readInt());
    lines.push('  out->message= "' + rstr(res.add(0x08)) + '"');
    if (err) lines.push('  异常: ' + err);
    return lines.join('\n');
  },

  // 读摄像机当前状态
  cam: function () {
    const base = Process.getModuleByName('hoi4.exe').base;
    const obj = base.add(0x332F698).readPointer();
    if (obj.isNull()) return 'idler NULL';
    const c = obj.add(0x750).readPointer();
    if (c.isNull()) return 'cam NULL';
    return '+0x69C(目标)=' + c.add(0x69C).readFloat().toFixed(2) +
           '  +0x678(当前)=' + c.add(0x678).readFloat().toFixed(2) +
           '  +0x698=' + c.add(0x698).readFloat().toFixed(2);
  }
};
