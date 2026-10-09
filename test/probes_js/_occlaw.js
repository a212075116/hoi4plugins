'use strict';
const GET_OCC = 0xff3be0;
let total = 0, nullCount = 0;
const samples = [];

function describeObj(p) {
  if (p.isNull()) return '(null)';
  try {
    const vt = p.readPointer();
    return 'obj=' + p + ' vt=' + vt + ' vtRva=' + vt.sub(Process.getModuleByName('hoi4.exe').base);
  } catch (e) { return 'obj=' + p + ' (unreadable)'; }
}

function readTag(p) {
  if (p.isNull()) return '(null ptr)';
  try {
    const s = p.readUtf8String();
    if (s && s.length > 0 && s.length <= 10) return 'str=' + s;
  } catch (e) { }
  try { return 'u32=' + p.readU32() + ' u16=' + p.readU16(); } catch (e) { return '(unreadable)'; }
}

rpc.exports = {
  install: function () {
    const m = Process.getModuleByName('hoi4.exe');
    Interceptor.attach(m.base.add(GET_OCC), {
      onEnter: function (args) {
        total++;
        this.rcx = args[0];
        this.tag = args[1];
      },
      onLeave: function (ret) {
        if (ret.isNull()) {
          nullCount++;
          if (samples.length < 15) {
            samples.push('#' + total + '  NULL  ' + describeObj(this.rcx) + '  tagPtr=' + this.tag + '  tag: ' + readTag(this.tag));
          }
        }
      }
    });
    return 'hooked ' + m.base.add(GET_OCC);
  },
  stats: function () { return 'total=' + total + ' null=' + nullCount; },
  dump: function () { return samples.length ? samples.join('\n') : '(none)'; }
};
