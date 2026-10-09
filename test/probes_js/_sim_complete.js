
'use strict';
const MGR_RVA = 0x35E1A80;
const ENTRY   = 456;

rpc.exports = {
  // 完全复刻补全函数的遍历: 对每条命令读 +0x28 个 char*, 逐个 strlen
  simulateComplete: function () {
    const base = Process.getModuleByName('hoi4.exe').base;
    const mgr = base.add(MGR_RVA).readPointer();
    const data = mgr.readPointer();
    const count = mgr.add(12).readInt();
    let total = 0, bad = 0, maxAlias = 0;
    const badList = [];
    for (let i = 0; i < count; i++) {
      const e = data.add(i * ENTRY);
      let n;
      try { n = e.add(0x28).readInt(); } catch (x) { badList.push('[' + i + '] 读 +0x28 失败'); continue; }
      if (n < 0 || n > 16) {
        badList.push('[' + i + '] +0x28 = ' + n + ' 异常');
        bad++;
        continue;
      }
      if (n > maxAlias) maxAlias = n;
      for (let k = 0; k < n; k++) {
        total++;
        let p = null;
        try { p = e.add(0x30 + k * 8).readPointer(); } catch (x) {
          badList.push('[' + i + '] 别名[' + k + '] 读指针失败'); bad++; continue;
        }
        if (p.isNull()) { badList.push('[' + i + '] 别名[' + k + '] 为空指针'); bad++; continue; }
        try {
          const s = p.readCString();
          if (s === null) { badList.push('[' + i + '] 别名[' + k + '] 无法读字符串'); bad++; }
        } catch (x) {
          badList.push('[' + i + '] 别名[' + k + '] @' + p + ' strlen 会崩: ' + x); bad++;
        }
      }
    }
    const L = [];
    L.push('命令总数          = ' + count);
    L.push('别名指针总数      = ' + total);
    L.push('单个命令最多别名  = ' + maxAlias);
    L.push('可疑项            = ' + bad);
    if (badList.length) {
      L.push('可疑列表 (前 20):');
      for (const s of badList.slice(0, 20)) L.push('   ' + s);
    } else {
      L.push('结论: 全部安全, 补全函数遍历不会越界');
    }
    return L.join('\n');
  }
};
