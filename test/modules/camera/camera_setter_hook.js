'use strict';
const RVA_SETH = 0x12643F0;
const MGR_RVA = 0x35E1A80;
const ENTRY = 456;
let LOG = [];

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
function wstr(p, s) {
  const bytes = [];
  for (let i = 0; i < s.length; i++) bytes.push(s.charCodeAt(i) & 0xff);
  const n = bytes.length;
  if (n <= 15) {
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
function camPtr() {
  const img = Process.getModuleByName('hoi4.exe').base;
  return img.add(0x332F698).readPointer().add(0x750).readPointer();
}

rpc.exports = {
  install: function () {
    const m = Process.getModuleByName('hoi4.exe');
    Interceptor.attach(m.base.add(RVA_SETH), {
      onEnter: function (args) {
        if (LOG.length > 40) return;
        let bt = [];
        try { bt = Thread.backtrace(this.context, Backtracer.ACCURATE).slice(0, 3).map(function (x) { return x.sub(m.base).toString(); }); } catch (e) { }
        LOG.push('  setter(cam=' + args[0] + ', h=' + args[1].toFloat() + ') tid=' + Process.getCurrentThreadId() + ' from=' + bt.join(' < '));
      }
    });
    return 'hooked setter @' + m.base.add(RVA_SETH);
  },
  log: function () { return LOG.length ? LOG.join('\n') : '  (无调用)'; },
  clear: function () { LOG = []; return 'cleared'; },
  state: function () {
    const c = camPtr();
    return '+678=' + c.add(0x678).readFloat().toFixed(2) +
           '  +69C=' + c.add(0x69C).readFloat().toFixed(2) +
           '  +680=' + c.add(0x680).readFloat().toFixed(2);
  },
  exec: function (name, args) {
    const base = Process.getModuleByName('hoi4.exe').base;
    const mgr = base.add(MGR_RVA).readPointer();
    const data = mgr.readPointer();
    const count = mgr.add(12).readInt();
    let entry = null;
    for (let i = 0; i < count; i++) {
      const e = data.add(i * ENTRY);
      if (rstr(e.add(0x08)) === name) { entry = e; break; }
    }
    if (!entry) return '命令未找到: ' + name;
    const handler = entry.add(0x68).readPointer();
    const n = args.length;
    const strArr = Memory.alloc(32 * Math.max(n, 1));
    for (let i = 0; i < n; i++) wstr(strArr.add(i * 32), args[i]);
    const cmdArgs = Memory.alloc(0x20);
    cmdArgs.writePointer(strArr);
    cmdArgs.add(8).writeInt(Math.max(n, 1));
    cmdArgs.add(12).writeInt(n);
    const res = Memory.alloc(0x60);
    for (let i = 0; i < 0x60; i++) res.add(i).writeU8(0);
    const fn = new NativeFunction(handler, 'pointer', ['pointer', 'pointer']);
    fn(res, cmdArgs);
    return 'ok=' + res.readInt() + ' msg="' + rstr(res.add(0x08)) + '"';
  }
};
