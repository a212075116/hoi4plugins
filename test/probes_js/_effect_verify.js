
'use strict';
const IMG = 0x140000000;
function img(ea) { return Process.getModuleByName('hoi4.exe').base.add(ea - IMG); }
const A_EFFECT_MAP = 0x143330000;

// MSVC std::map 节点: {left@0, parent@8, right@0x10, isnil@0x18(byte), pad, key@0x20, value@0x28}
function walk(root, wantId) {
  const found = [];
  let count = 0;
  const stack = [root];
  while (stack.length) {
    const n = stack.pop();
    if (n.isNull()) continue;
    count++;
    if (count > 200000) break;
    try {
      if (n.add(0x19).readU8() !== 0) continue;   // isnil -> 叶子
      const key = n.add(0x20).readInt();
      const val = n.add(0x28).readPointer();
      if (wantId === null || key === wantId) found.push({ key: key, val: val, node: n });
      stack.push(n.readPointer());                 // left
      stack.push(n.add(0x10).readPointer());       // right
    } catch (e) { }
  }
  return { found: found, count: count };
}

rpc.exports = {
  verify: function (wantId) {
    const map = img(A_EFFECT_MAP).readPointer();
    if (map.isNull()) return 'map NULL';
    // std::map 对象: _Myhead 在 +0x00，size 在 +0x08
    const head = map.readPointer();
    const size = map.add(8).readU64().toNumber();
    const L = [];
    L.push('map = ' + map + '  head = ' + head + '  size = ' + size);
    if (head.isNull()) return L.join('\n') + '\nhead NULL';
    // head->parent 是根
    const root = head.add(8).readPointer();
    L.push('root = ' + root);
    const r = walk(root, wantId);
    L.push('遍历节点数 = ' + r.count);
    if (wantId !== null) {
      if (r.found.length === 0) L.push('** 未找到 id=' + wantId + ' **');
      for (const f of r.found) {
        L.push('找到 id=' + f.key + '  node=' + f.node + '  value(entry)=' + f.val);
        try {
          L.push('   entry->vftable = ' + f.val.readPointer());
          L.push('   entry->desc    = "' + f.val.add(8).readPointer().readUtf8String() + '"');
        } catch (e) { L.push('   读取 entry 失败: ' + e); }
      }
    }
    return L.join('\n');
  }
};
