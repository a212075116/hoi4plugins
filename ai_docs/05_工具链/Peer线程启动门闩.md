# Peer线程启动门闩

2026-10-14，第二十四批源码规范化。

## 当前启动合同

`StartPeerThreads`集中持有5个新线程的启动句柄，线程先进入`PeerStart`，通过原子`g_peerState`等待本轮启动提交。
只有5个CreateThread全部成功，服务才提交`g_started=2`，随后发布`g_peerState=1`，允许进入原有Peer。
等待只发生在启动阶段，Sleep(1)不是常驻命令队列轮询，也没有新增门闩事件句柄。

任一创建失败，立即发布`g_peerState=-1`，已创建的包装线程不进入Peer；启动者等待这些线程退出并关闭拥有的线程句柄。
随后设置`g_failed=1`、`g_started=-1`，释放pipe和完成事件，返回8；不打印ready、不自动打开helper、不自动重试。
初始服务线程CreateThread失败也设置`g_started=-1`并记录错误，此时尚未创建pipe、事件或scheduler。

## 所有权与保留边界

失败清理前已经等待所有本轮包装线程结束，因此没有活动Peer持有被关闭的pipe。
成功时关闭线程句柄不会终止线程；pipe、完成事件和工作线程仍按既有process生命期拥有。
Peer、Frame、Execute、权限、请求格式、队列和正常命令语义未修改。

Peer创建失败时保留已安装scheduler及原函数槽位，Frame由g_failed跳过队列；不贸然Remove可能正被回调使用的trampoline。
这是安全停用桥接，不是成功删除hook，也不是支持热卸载或故障后重新启用。
其他早期启动失败的既有状态规则没有整体改写。

## 证据

- 实际StartDebugService/adapter夹具67场景，覆盖每个Peer创建失败位置；新版8425检查、0失败。
- 旧版及精确恢复版均有240个新合同断言失败，证明旧ready误报仍在；完整stdout一致。
- 实际PeerStart/StartPeerThreads/DebugConsole_Start使用真实Win32线程和句柄，32个失败掩码各重复16次，共512轮。
- 门闩提交前Peer调用为0，失败后Peer调用为0，成功放行后为5；全部拥有的句柄关闭后进程句柄数恢复。
- 初始服务线程创建失败、禁止自动重试也由实际入口验证。

受控Peer不执行游戏命令；上述不是所有长期并发/热卸载的证明。
测试、实机与回滚见[Peer启动回归](../../test/docs/peer_startup.md)。
