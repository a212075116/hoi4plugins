# 批量Hook启用与创建所有权

2026-10-14，第十八批，三个成就模块真实共同操作收拢。

## 两个私有机制

`SDK_RVA/hook/inline_hook_batch.h`提供：

```c
int InlineHook_EnableQueuedBatch(void* const* targets, int count);
void InlineHook_CleanupCreatedBatch(void* const* targets, int count);
```

前者按原顺序QueueEnable，首个失败即返回0，全部排队后ApplyQueued一次。
后者针对本轮成功Create的前缀：逐个QueueDisable及立即Disable，ApplyQueued一次，再按创建顺序Remove。
调用者必须已初始化MinHook，提供合法targets和实际created数量；不新增参数校验、状态或内存分配。
兼容、原版来源及UI安装器复用这两段代码；各自Create、目标RVA、trampoline输出、host检查、提交标志不变。
第十八批单hook适配器及第三方MinHook保持原字节；当前[第十九批](../05_工具链/服务端Scheduler安装与原函数发布.md)为单hook增加发布槽位接口并复用实现，旧接口行为保持。

## 所有权及未强化的策略

created只在MH_CreateHook返回MH_OK后增加；AlreadyCreated失败目标不是本轮所有，不进入Remove列表。
UI第一项Create失败原本直接返回；仍如此，不额外ApplyQueued。
另外两模块created=0进入失败分支，原本仍ApplyQueued一次；共享cleanup保留这个行为。
cleanup的QueueDisable/Disable/Apply/Remove失败仍被原调用者忽略，属于best-effort，不能宣称总能删除或恢复。
MinHook队列是全局的，ApplyQueued可能应用其他排队操作；不是独立事务隔离，也不改变全局队列时序。
没有新增线程同步、trampoline生命周期保障或消除间歇退出的声明。

## 执行证据

实际单hook适配器及三个生产安装函数，受控MinHook状态模型1019场景、3381项检查，三态stdout/stderr/exit完全一致、零失败。
覆盖各Create/Queue/Apply失败点、AlreadyCreated foreign目标、清理失败组合、init失败、null目标及单hook启用/移除失败顺序。
三组实际成就业务夹具31/16/12三态通过，Debug/Release及源码/DLL副本回滚通过。
测试不安装真实hook，不连接Steam；新DLL仅归档，未部署或进入游戏。
服务端scheduler的Create/Enable失败路径已由第十九批独立夹具及清理修正覆盖，不把本批当作所有hook生命周期已解决。
测试说明见[hook批量机制回归](../../test/docs/hook_batch.md)。
