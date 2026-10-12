# Effect Scope 与 scoped 操作数验证

2026-10-12，当前本地游戏版本。结论：不能把所有 Effect 都当成国家专用，也不能把 Any 当成任意对象都有变量容器。

## 合约与修复

原版执行包装 RVA 0x53D9E0 经 0x540810 检查实例虚表 +0x98 返回的 mask；0 表示不限 scope。
本轮上下文采样国家=4、州=2、角色=8，来自 Effect helper 0x537D90。
这些是 Effect 上下文证据，不可拿去解释 Trigger 上下文布局。

通用注册器继承 CAddStabilityEffect，默认仅国家。新可选字段 `EffectDef.supportedScopes`
允许定义选择 getter；摄像机/日期显式选择 `Effect_ScopeAny`，原版 gate 仍在。
变量模板继承原版 CSetVariableEffect 的 mask=0，未改变其 scope/container 规则。
国家、州、角色各有自己的变量容器；`global.name` 指向全局变量容器，不是通用 scope 的同义词。

旧版读取 scoped 操作数时错误复用目标 descriptor +88，导致 ROOT 的 2.5 被读成原生低位整数 2。
现由 `Var64_ReadStoredOperandAt` 使用操作数自己的 descriptor：+296，clamp 最大值 +504。
`Var64_ContainerAt` 调原版 resolver 0x542500；`Var64_ReadStoredIn` 在该容器只读验证完整三槽并重组 raw。
不创建缺失操作数、不按同名变量跨容器搜索；非持久化 variable64 仍交回原版参数读取路径。

## 游戏观察

| 输入/场景 | 基线 | 修改版 |
|---|---|---|
| 国家/另一国家/州/角色，12345.125 + 0.25 | 均 12345.375 | 均 12345.375 |
| global 10000000000.125 + 0.25 | 10000000000.375 | 相同 |
| ARI 中 10 × ROOT.sc_operand，ROOT=2.5，ARI 同名原生变量=9.5 | 20（错误） | 25 |
| 全局日期/摄像机零增量 | mask=4，州/角色拒绝，8 条错误 | mask=0，8 次回调、无相关错误 |

修改版额外实测：ROOT clamp=7.75、PREV 操作数=25、global 操作数=12.5、
ROOT 目标写入=5.125、子事件 FROM 操作数=45；原国家同名变量仍为 12345.375。
游戏存活。数值 oracle 12/12，scope callback/mask 单独校验通过。

## 复现与证据链

`python -u test/modules/effect/verify_effect_scopes.py PHASE` 需先完成 Release x64 构建及部署；
会安装测试事件、重启游戏、执行 zzscopecheck.1。PHASE 必须全新以保护旧证据。
`python test/modules/effect/verify_effect_scopes.py modified --verify-only` 可重查捕获记录。

Evidence：`test/reports/20261012_variable64_transaction/scope/baseline`、`modified` 的事件、日志、samples、report。
Finding：继承国家限制与目标/操作数容器混用是两个独立问题。
Path：仅全局 Effect 改 scope getter；变量改操作数容器读取；同输入原生夹具验证 baseline=20、modified=25、rollback=20，且原始哈希恢复。
原生夹具编译实际 `Var64_TryDebtArithmetic`，mock 原版解析依赖；不是第三次游戏回滚实测。

修复后再执行存档—退出—重启读档的 3060 次算术调用矩阵：516/516 断言通过。
旧用例 48/48、污染 0；饱和算术原生属性测试 10676/10676，身份夹具 8/8，长名桥接 6/6。
Release x64 最终构建退出码 0、无警告。以上是本轮测试输入的覆盖，不是无限运行保证。

## 边界

未声称支持任意不具备原版变量容器的 scope，也未完成全部 ROOT/PREV/FROM 链、无 scope 回调、
跨对象存档往返、挂账操作数持久化、多人同步、多线程、长时间运行或 UI 视觉验收。
后续数值/block Trigger与typed scope adapter已实现并验证，见[typed模板](../10_Trigger系统/数值块模板与Scope适配.md)；仍不能借用Effect offset。
