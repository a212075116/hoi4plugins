
'use strict';
const IMG = 0x140000000;
function img(ea) {   // IDA 绝对地址 -> 运行时绝对地址
  return Process.getModuleByName('hoi4.exe').base.add(ea - IMG);
}

const A_FLAG_INIT  = 0x1435E1AB0;
const A_FLAG_SYNC  = 0x1435E1AB1;
const A_DYN_DATA   = 0x1435E1AC0;
const A_DYN_COUNT  = 0x1435E1ACC;
const A_NAME_TABLE = 0x1435E1AE0;
const A_ADD_HI     = 0x1424BB460;
const A_ADD_LO     = 0x1424BB500;
const A_NAME_OF_ID = 0x1424BC260;

rpc.exports = {
  probe: function () {
    const L = [];
    L.push('hoi4 base = ' + Process.getModuleByName('hoi4.exe').base);
    L.push('');
    L.push('lexer initialized (0x1435E1AB0)       = ' + img(A_FLAG_INIT).readU8());
    L.push('lexer sync initialized (0x1435E1AB1)  = ' + img(A_FLAG_SYNC).readU8());
    L.push('dyn count (dword_1435E1ACC)           = ' + img(A_DYN_COUNT).readInt());
    L.push('dyn data  (qword_1435E1AC0)           = ' + img(A_DYN_DATA).readPointer());
    L.push('name table(qword_1435E1AE0)           = ' + img(A_NAME_TABLE).readPointer());
    L.push('');
    L.push('AddDynamicToken(hi) @ ' + img(A_ADD_HI));
    L.push('AddDynamicToken(lo) @ ' + img(A_ADD_LO));
    L.push('NameOfId        @ ' + img(A_NAME_OF_ID));
    return L.join('\n');
  },

  addToken: function (name) {
    const outId = Memory.alloc(8);
    outId.writeInt(0x7FFFFFFF);
    const strBuf = Memory.allocUtf8String(name);
    const view = Memory.alloc(16);
    view.writePointer(strBuf);
    view.add(8).writeU64(name.length);

    const fn = new NativeFunction(img(A_ADD_HI), 'pointer', ['pointer', 'pointer', 'pointer']);
    let err = null;
    try { fn(outId, view, ptr(0)); } catch (e) { err = String(e); }

    const L = [];
    L.push('AddDynamicToken("' + name + '")');
    L.push('  out_id = ' + outId.readInt());
    if (err) L.push('  err    = ' + err);
    return L.join('\n');
  },

  nameOfId: function (id) {
    const fn = new NativeFunction(img(A_NAME_OF_ID), 'pointer', ['int']);
    try {
      const p = fn(id);
      const cap = p.add(0x18).readU64().toNumber();
      const size = p.add(0x10).readU64().toNumber();
      const bp = (cap <= 15) ? p : p.readPointer();
      if (size <= 0 || size > 200) return 'id ' + id + ' -> (size=' + size + ')';
      return 'id ' + id + ' -> "' + bp.readUtf8String(size) + '"';
    } catch (e) { return 'id ' + id + ' -> 失败: ' + e; }
  }
};
