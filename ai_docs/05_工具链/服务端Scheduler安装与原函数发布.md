# 服务端Scheduler安装与原函数发布

2026-10-14，第十九批，复用单hook适配器并保持Frame原函数发布顺序。

本篇为第十九批历史证据，不是当前全部启动状态合同；现用夹具已扩展，Peer故障和启动提交见[第二十四批](Peer线程启动门闩.md)。

## 共享机制

新增模块接口 `InlineHook_InstallInto(target, detour, original)`。
目标/回调/输出槽位必须有效；NULL参数返回0，不调用MinHook或修改输出。
CreateHook直接写调用方original槽位，然后Enable；因此回调在Enable期间即可读取原函数。
创建失败返回0且不移除失败目标；创建成功但Enable失败时按原适配器策略Remove本轮hook，再返回0。
Remove失败仍是best-effort，不把残留对象伪装为已恢复。

旧 `InlineHook_Install`保留返回值契约，使用局部original并委托新实现；原有调用/错误策略不变。
没有复制另一份Create/Enable处理，也没有新增线程、分配器或第三方修改。

## 服务端调用

`StartDebugService`保留显式Init及g_thread条件，然后调用InstallInto写 `g_frame`。
不能直接使用“Enable之后才返回orig”的接口再赋全局，否则Frame可能先执行而看不到原函数。
既有pipe/event都先准备，再启用Frame，再启动Peer并提交started=2，成功顺序不变。
失败返回码、token/SID/ACL、pipe flags、事件及Peer参数、自动打开/禁止打开参数保持原样。
启用失败现在尝试清理本轮创建的scheduler，随后按原顺序关闭pipe/events；foreign hook不进入清理。
失败后的g_started仍保留原规则，不在此批新加重试或清空其他全局状态。

适配器诊断日志由共同实现继承，可能比原来多一条hook诊断；服务端提示和协议不改。
host module地址只获取一次供Create/Enable使用，不保留原来冗余的第二次同址查找。

## 证据及边界

真实启动函数及适配器配合受控native API，25场景：基线4379检查、2失败、exit1；修改版4385检查、0失败、exit0；回滚恢复基线stdout。
23个非修正路径的资源/hook摘要一致；Create/Enable前后的trampoline发布断言、foreign保留、Remove失败残留均通过。
新接口三个NULL输入及输出/调用不变检查单独通过。
旧单hook适配器及三个批量安装器1019场景仍三态完全一致；成就31/16/12、console/log17及Debug/Release通过。
源码/DLL副本回滚与完整包重建通过，未部署或运行真实服务/游戏。

其余UI/process/variable64共享原函数保存点已由[第二十批](../03_插件/原函数预发布与数值Hook绑定.md)单独迁移并检查，不能把本批当作所有并发或trampoline生命周期已解决。
实际运行时指令与GUI集成仍在全项目验收范围；见[启动夹具记录](../../test/docs/service_scheduler.md)。
