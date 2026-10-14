# 服务端Scheduler启动三态回归

2026-10-14，第十九批。

本篇保留第十九批25场景结果；现用同名脚本已扩为67场景，当前Peer故障合同及真实线程专项见[第二十四批](peer_startup.md)。

## 执行

从项目根运行：

```powershell
python test/modules/console/test_service_scheduler.py SOURCE_ROOT OUTPUT
```

MSVC x64，完整源根，独立输出目录。夹具提取生产 `StartDebugService`及Pending类型，包含实际单hook适配器。
token、SID、安全描述符、pipe、event、window thread、Peer创建及MinHook是受控替身，不启动线程或修改游戏。
检查原函数在Enable调用时已发布，而不是只在启动返回后看值。

| 观察 | BASELINE | MODIFIED | ROLLBACK |
|---|---|---|---|
| 原生启动场景 | 25 | 25 | 25 |
| 检查/失败 | 4379/2 | 4385/0 | 4379/2 |
| 执行状态 | exit1 | exit0 | exit1 |
| 23个非修正路径 | 资源/hook摘要 | 完全一致 | 完全一致 |
| 本轮Create成功、Enable失败 | 未尝试Remove | 尝试Remove，仅清理本轮hook | 恢复旧遗漏 |

修改版新增两次Remove调用检查，以及四项新接口NULL/输出原子性检查。
Remove失败场景明确保留残留：通过的是正确尝试及错误策略，不是保证成功删除。
foreign AlreadyCreated目标保持，不启用、不删除；原g_started失败策略不变。
覆盖host指纹、token/分配/ACL失败、普通/交互pipe失败、event失败、缺失game thread、Init失败、peer创建失败及auto-open/no-plugin参数。
新共同诊断日志及少一次冗余module lookup不列入“所有可见日志/WinAPI调用完全相同”的承诺。

基线/回滚stdout完全一致，stderr空，编译exit0；业务成就31/16/12、console/log17三态一致。
原适配器和批量安装器1019场景三态不变，Debug/Release及源码/DLL副本回滚通过。

## 归档

报告：`test/reports/20261014_service_scheduler/`。
复用 `test/reports/20261012_variable64_transaction/`四角色：
`MODIFIED_FILE.zip`、`DIFF_FILE.patch`、`VERIFICATION.txt`、`ROLLBACK.sh`。
回滚脚本对 `*.service-scheduler.zip`或 `*.service-scheduler.dll`恢复本批基线，完整包另验证binary patch和最初基线回滚。
没有部署、调用真实token/pipe/thread/Steam或进入游戏；其他共享callback发布点已由[第二十批](original_publication.md)复核，完整运行生命周期仍未由局部夹具证明。
设计见[Scheduler安装与原函数发布](../../ai_docs/05_工具链/服务端Scheduler安装与原函数发布.md)。
