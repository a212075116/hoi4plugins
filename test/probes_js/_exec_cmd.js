
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

const FILELOG = [];
let fileHookCount = 0;
function installFileHook() {
  const targets = [['kernel32.dll', 'CreateFileW'], ['kernel32.dll', 'CreateDirectoryW']];
  for (let k = 0; k < targets.length; k++) {
    let a = null;
    try { a = Process.getModuleByName(targets[k][0]).getExportByName(targets[k][1]); } catch (e) { continue; }
    if (!a) continue;
    try {
      Interceptor.attach(a, {
        onEnter: function (args) {
          try {
            const p = args[0];
            if (p.isNull()) return;
            const s = p.readUtf16String();
            if (!s) return;
            if (s.indexOf('crash') >= 0 || s.indexOf('Crash') >= 0 ||
                s.indexOf('.dmp') >= 0 || s.indexOf('meta.yml') >= 0 ||
                s.indexOf('exception.txt') >= 0) {
              const line = targets[k][1] + '  ' + s + '\n';
              if (FILELOG.length < 300) FILELOG.push(line.trim());
              try {
                const f = new File('D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/filehook.log', 'a');
                f.write(line);
                f.flush();
                f.close();
              } catch (e) { }
            }
          } catch (e) { }
        }
      });
      fileHookCount++;
    } catch (e) { }
  }
  return fileHookCount;
}

let procHookCount = 0;
function installProcHook() {
  const names = ['CreateProcessW', 'CreateProcessA'];
  for (let i = 0; i < names.length; i++) {
    let a = null;
    try { a = Process.getModuleByName('kernel32.dll').getExportByName(names[i]); } catch (e) { continue; }
    if (!a) continue;
    try {
      Interceptor.attach(a, {
        onEnter: function (args) {
          try {
            let s = null;
            const p = args[1].isNull() ? args[0] : args[1];
            if (p.isNull()) return;
            s = (names[i] === 'CreateProcessW') ? p.readUtf16String() : p.readAnsiString();
            if (!s) return;
            const line = names[i] + '  ' + s + '\n';
            try { const f = new File('D:/SteamLibrary/steamapps/common/Hearts of Iron IV/reports/prochook.log', 'a'); f.write(line); f.flush(); f.close(); } catch (e) { }
          } catch (e) { }
        }
      });
      procHookCount++;
    } catch (e) { }
  }
  return procHookCount;
}

rpc.exports = {
  hookProc: function () { return 'procHooked=' + installProcHook(); },
  hookFiles: function () { return 'hooked=' + installFileHook(); },
  fileLog: function () { return FILELOG.length ? FILELOG.join('\n') : '(nothing captured)'; },

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

  // 就绪探测: 返回 {ok, idler, cam, h}
  ready: function () {
    const base = Process.getModuleByName('hoi4.exe').base;
    const idler = base.add(0x332F698).readPointer();
    if (idler.isNull()) return { ok: false, why: 'idler NULL' };
    try {
      const cam = idler.add(0x750).readPointer();
      if (cam.isNull()) return { ok: false, why: 'cam NULL', idler: idler.toString() };
      if (cam.toUInt32() < 0x10000) return { ok: false, why: 'cam bogus', idler: idler.toString() };
      const h = cam.add(0x69C).readFloat();
      if (!(h >= 50.0 && h <= 3000.0)) return { ok: false, why: 'height out of range ' + h };
      return { ok: true, idler: idler.toString(), cam: cam.toString(), h: h };
    } catch (e) { return { ok: false, why: String(e) }; }
  },

  // 只返回高度数值
  camHeight: function () {
    const base = Process.getModuleByName('hoi4.exe').base;
    const idler = base.add(0x332F698).readPointer();
    if (idler.isNull()) return -1.0;
    try {
      const cam = idler.add(0x750).readPointer();
      if (cam.isNull()) return -1.0;
      return cam.add(0x69C).readFloat();
    } catch (e) { return -1.0; }
  },

  // 读摄像机高度与相邻字段的原始字节 (判断 int / float)
  camLimits: function () {
    const base = Process.getModuleByName('hoi4.exe').base;
    const idler = base.add(0x332F698).readPointer();
    if (idler.isNull()) return 'idler NULL';
    const cam = idler.add(0x750).readPointer();
    if (cam.isNull()) return 'cam NULL';
    const out = [];
    const offs = [0x69C, 0x6D0, 0x6D4, 0x6D8, 0x6DC, 0x6F4, 0x6F8, 0x6FC];
    for (let k = 0; k < offs.length; k++) {
      const o = offs[k];
      out.push('  +0x' + o.toString(16) +
               '  u32=' + cam.add(o).readU32() +
               '  i32=' + cam.add(o).readS32() +
               '  f32=' + cam.add(o).readFloat().toFixed(4));
    }
    return out.join('\n');
  },

  // 列出控制台命令里名字含关键字的
  listCmds: function (needle) {
    const base = Process.getModuleByName('hoi4.exe').base;
    const mgr = base.add(0x35E1A80).readPointer();
    if (mgr.isNull()) return 'mgr NULL';
    const data = mgr.readPointer();
    const count = mgr.add(12).readInt();
    const out = [];
    for (let i = 0; i < count; i++) {
      const e = data.add(i * 456);
      const n = rstr(e.add(0x08));
      if (!needle || n.indexOf(needle) >= 0) out.push(n);
    }
    return 'count=' + count + '  matched=' + out.length + '\n' + out.join('\n');
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
