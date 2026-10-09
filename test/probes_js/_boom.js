'use strict';
rpc.exports = {
  boom: function () {
    // 制造一次真正的访问违规, 交给游戏自己的崩溃处理器
    const p = ptr(0x1);
    p.writeU8(0);
    return 'unreachable';
  }
};
