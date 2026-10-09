'use strict';
// effect 注册表: qword_143330000 = std::map<int, CEffectEntryBase*>
// 遍历红黑树比较麻烦, 直接用游戏自己的查找函数 sub_14206CDC0? 不对那是 token。
// 这里用另一个办法: hook 注册函数 sub_1405415A0, 记录所有已注册的 effect 描述。
// 但注册在很早发生, 改用读 map 的方式: std::map 的 _Myhead->_Left 是根节点。
const MAP = 0x3330000;
function m_() { return Process.getModuleByName('hoi4.exe'); }
function readCStr(p) {
  try { return p.readUtf8String(); } catch (e) { return null; }
}
rpc.exports = {
  // 遍历 std::map (MSVC): _Myhead at [map], 节点: _Left(0) _Parent(8) _Right(0x10) _Isnil(0x18) _Myval(0x20)
  dump: function (filter) {
    const m = m_();
    const head = m_.base; 
    const mapAddr = m.base.add(MAP);
    const headPtr = mapAddr.readPointer();   // std::map 对象首字段是 _Myhead
    if (headPtr.isNull()) return 'map head null';
    const out = [];
    const seen = {};
    const stack = [headPtr.add(0x10)];   // root = _Myhead->_Right
    let guard = 0;
    while (stack.length && guard < 4000) {
      guard++;
      const n = stack.pop();
      if (n.isNull()) continue;
      const isnil = n.add(0x18).readU8();
      if (isnil) continue;
      try {
        const key = n.add(0x20).readS32();
        const entry = n.add(0x28).readPointer();
        let desc = null, name = null;
        if (!entry.isNull()) {
          desc = readCStr(entry.add(8).readPointer());
        }
        const label = (desc || '') + ' #' + key;
        if (!filter || label.toLowerCase().indexOf(filter.toLowerCase()) >= 0) {
          if (!seen[label]) { seen[label] = 1; out.push('  key=' + key + '  ' + desc); }
        }
        stack.push(n.add(0x10));
        stack.push(n.add(0x0));
      } catch (e) { }
    }
    return 'found ' + out.length + '\n' + out.slice(0, 60).join('\n');
  },
  count: function () {
    const m = m_();
    const headPtr = m.base.add(MAP).readPointer();
    let n = 0;
    const stack = [headPtr.add(0x10)];
    let guard = 0;
    while (stack.length && guard < 4000) {
      guard++;
      const nd = stack.pop();
      if (nd.isNull()) continue;
      if (nd.add(0x18).readU8()) continue;
      n++;
      stack.push(nd.add(0x10));
      stack.push(nd.add(0x0));
    }
    return n;
  }
};
