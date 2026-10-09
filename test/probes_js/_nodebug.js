'use strict';
let blocked = 0, passed = 0;
const log = [];
function setup(name, wide) {
  const addr = Process.getModuleByName('kernel32.dll').getExportByName(name);
  if (!addr) return false;
  const OrigFn = new NativeFunction(addr, 'int', ['pointer','pointer','pointer','pointer','int','uint','pointer','pointer','pointer','pointer']);
  Interceptor.replace(addr, new NativeCallback(function (a0, a1, a2, a3, a4, a5, a6, a7, a8, a9) {
    try {
      let s = null;
      if (!a1.isNull()) {
        try { s = wide ? a1.readUtf16String(300) : a1.readAnsiString(300); } catch (e) { }
      }
      if (!s && !a0.isNull()) {
        try { s = wide ? a0.readUtf16String(300) : a0.readAnsiString(300); } catch (e) { }
      }
      if (s && s.indexOf('notepad') >= 0 && s.indexOf('error.log') >= 0) {
        blocked++;
        if (log.length < 10) log.push('拦下 ' + name + ': ' + s.slice(0, 150));
        return 0;   // FALSE, 不执行原函数
      }
      passed++;
    } catch (e) { }
    return OrigFn(a0, a1, a2, a3, a4, a5, a6, a7, a8, a9);
  }, 'int', ['pointer','pointer','pointer','pointer','int','uint','pointer','pointer','pointer','pointer']));
  return true;
}
rpc.exports = {
  install: function () { return 'A=' + setup('CreateProcessA', false) + ' W=' + setup('CreateProcessW', true); },
  state: function () { return 'blocked=' + blocked + '  passed=' + passed; },
  dump: function () { return log.length ? log.join('\n') : '(none)'; }
};
