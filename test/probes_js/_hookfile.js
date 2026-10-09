'use strict';
const LOG = [];
let hooked = 0;
let errs = [];

function findExport(mod, name) {
  try {
    const m = Process.getModuleByName(mod);
    return m.getExportByName(name);
  } catch (e) { errs.push(mod + '!' + name + ' : ' + e); return null; }
}

function install() {
  const targets = [['kernel32.dll', 'CreateFileW'], ['kernel32.dll', 'CreateDirectoryW']];
  for (let k = 0; k < targets.length; k++) {
    const mod = targets[k][0], nm = targets[k][1];
    const a = findExport(mod, nm);
    if (!a) continue;
    try {
      Interceptor.attach(a, {
        onEnter: function (args) {
          try {
            const p = args[0];
            if (p.isNull()) return;
            const s = p.readUtf16String();
            if (!s) return;
            if (s.indexOf('crash') >= 0 || s.indexOf('Crash') >= 0 || s.indexOf('.dmp') >= 0 || s.indexOf('meta.yml') >= 0 || s.indexOf('exception.txt') >= 0) {
              if (LOG.length < 300) LOG.push(nm + '  ' + s);
            }
          } catch (e) { }
        }
      });
      hooked++;
    } catch (e) { errs.push('attach ' + nm + ' : ' + e); }
  }
  return hooked;
}

rpc.exports = {
  start: function () { const n = install(); return 'hooked=' + n + '  errs=' + errs.join(' | '); },
  dump: function () { return LOG.length ? LOG.join('\n') : '(nothing captured)'; },
  probe: function () {
    const out = [];
    try { out.push('Process.getModuleByName ok'); } catch (e) { out.push('Process.getModuleByName FAIL ' + e); }
    try { const m = Process.getModuleByName('kernel32.dll'); out.push('kernel32 base=' + m.base); } catch (e) { out.push('kernel32 FAIL ' + e); }
    try { const m = Process.getModuleByName('kernel32.dll'); out.push('CreateFileW=' + m.getExportByName('CreateFileW')); } catch (e) { out.push('getExportByName FAIL ' + e); }
    return out.join('\n');
  }
};
