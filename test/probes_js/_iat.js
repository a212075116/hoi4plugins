'use strict';
rpc.exports = {
  imports: function () {
    const m = Process.getModuleByName('hoi4.exe');
    const want = ['CreateFileW', 'CreateDirectoryW', 'CreateFileA', 'DeleteFileW', 'MoveFileW'];
    const out = [];
    let total = 0;
    try {
      const imps = m.enumerateImports();
      total = imps.length;
      for (let i = 0; i < imps.length; i++) {
        const im = imps[i];
        if (want.indexOf(im.name) >= 0) {
          out.push(im.type + '  ' + im.module + '!' + im.name + '  @ ' + im.address + '  slot=' + (im.slot || ''));
        }
      }
    } catch (e) { return 'enumerateImports FAIL: ' + e; }
    return 'hoi4.exe imports total=' + total + '  matched=' + out.length + '\n' + out.join('\n');
  }
};
