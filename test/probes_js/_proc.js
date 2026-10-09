'use strict';
const LOG = [];
function install() {
  let n = 0;
  const names = ['CreateProcessW', 'CreateProcessA', 'ShellExecuteW', 'ShellExecuteExW'];
  for (let i = 0; i < names.length; i++) {
    let a = null;
    try { a = Process.getModuleByName('kernel32.dll').getExportByName(names[i]); } catch (e) { continue; }
    if (!a) continue;
    try {
      Interceptor.attach(a, {
        onEnter: function (args) {
          try {
            let s = null;
            if (names[i] === 'CreateProcessW') { s = args[1].isNull() ? args[0].readUtf16String() : args[1].readUtf16String(); }
            else if (names[i] === 'CreateProcessA') { s = args[1].isNull() ? args[0].readAnsiString() : args[1].readAnsiString(); }
            else { s = args[0].readUtf16String(); }
            if (!s) return;
            const line = names[i] + '  ' + s + '\n';
            LOG.push(line.trim());
            try { const f = new File('` + W + `/reports/prochook.log', 'a'); f.write(line); f.flush(); f.close(); } catch (e) { }
          } catch (e) { }
        }
      });
      n++;
    } catch (e) { }
  }
  return n;
}
rpc.exports = {
  start: function () { return 'hooked=' + install(); },
  dump: function () { return LOG.length ? LOG.join('\n') : '(none)'; },
  imports: function () {
    const m = Process.getModuleByName('hoi4.exe');
    let r = [];
    try {
      const imps = m.enumerateImports();
      for (let i = 0; i < imps.length; i++) {
        const nm = imps[i].name;
        if (nm.indexOf('CreateProcess') === 0 || nm.indexOf('ShellExecute') === 0)
          r.push(imps[i].module + '!' + nm + '  slot=' + imps[i].slot);
      }
    } catch (e) { return 'fail ' + e; }
    return r.length ? r.join('\n') : '(no CreateProcess/ShellExecute imports)';
  }
};
