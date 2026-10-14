# 原函数预发布与数值Hook绑定

2026-10-14，第二十批。迁移真实共享original槽位并合并六段同规则安装。

## 当前调用方

日期UI1个、process A/W2个、variable64主setter1个及算术6个及语言桥1个槽位，均通过 `InlineHook_InstallInto`先发布，再Enable。
不再先Enable后把返回值赋到回调需要的全局original。
日期、进程、数值及scope业务函数不变，只调整安装器。
SDK返回值接口仍保留，不删掉兼容入口；生产消费者的共享槽位已迁移。

## 失败和重试策略

- 日期UI、进程及算术原先失败赋NULL，当前显式恢复同样的NULL状态。
- variable64主setter原先安装失败不改已有original，当前保存旧槽位并在失败后恢复。
- ready/installed标志、原检查条件、部分成功规则、未读取目标的保留规则及日志字段保持原样。
- 六个算术安装由函数内静态binding表描述RVA、detour和original；顺序仍add/sub/mul/div/clamp/clear，不新增round/modulo。
- Remove失败可能残留hook，其他线程/卸载生命周期未新加保证；不能把本批当作可任意重新安装或解除运行回调的证明。

没有新公有接口、线程、分配器或额外编译单元，使用上一批已验证的槽位接口。
输出槽位在安装期间必须可写，回调使用的存储必须有相应生命周期；普通函数局部返回值并不自动保证共享槽位预发布。

## 证据

生产UI及适配器、实际process/scalar安装定义：1360组missing/readability/failure/seed/ready配置，12170项检查。
基线1839项发布断言失败、exit1；修改版零失败、exit0；回滚恢复完整基线stdout。
去除发布观测字段后，三态最终槽位、标志和native操作序列完全一致。
UI回调是真实函数，以SEH捕获基线NULL故障；其他detour为要求正确槽位的受控入口，不宣称执行了完整业务。
各业务函数安装器之外限定文本一致；数值、日期、注册器和存储既有回归另执行，不以安装夹具替代业务。
Debug/Release、源码/DLL副本和完整包回滚通过，新DLL仅归档未部署。

本批只证明受控Enable期间的可见原函数，不证明所有线程内存顺序/移除安全，也不将其归因为用户暂缓的间歇退出。
执行入口见[原函数预发布三态回归](../../test/docs/original_publication.md)。
