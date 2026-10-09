'use strict';
function M() { return Process.getModuleByName('hoi4.exe'); }
rpc.exports = {
  read: function () {
    const m = M();
    const out = [];
    const addr = 0x332ECF0;
    try { out.push('全局 0x332ECF0 (i32) = ' + m.base.add(addr).readS32()); } catch (e) { out.push('读 0x332ECF0 失败: ' + e); }
    try { out.push('全局 0x332ECF0 (u32) = ' + m.base.add(addr).readU32()); } catch (e) { }
    // 附近几个 dword
    let near = [];
    for (let i = -4; i <= 4; i++) {
      try { near.push('+' + (i*4) + '=' + m.base.add(addr + i*4).readS32()); } catch (e) { }
    }
    out.push('邻域: ' + near.join('  '));
    // 反汇编确认 0x175b20 / 0x175b26
    return out.join('\n');
  }
};
