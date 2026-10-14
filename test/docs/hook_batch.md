# Hook批量机制与适配器三态回归

2026-10-14，第十八批，排队与owned-prefix清理复用。

## 入口

从项目根执行：

```powershell
python test/modules/hook/test_hook_batch.py SOURCE_ROOT OUTPUT
```

MSVC x64，源根完整src，输出独立目录。
夹具包含实际 `inline_hook.c`并提取三个安装器的真实定义；不复制生产分支为期望值。
MinHook由受控状态模型替代，记录Initialize/Create/Queue/Disable/Apply/Remove的序列及残留状态。

| 同输入观察 | BASELINE | MODIFIED | ROLLBACK |
|---|---|---|---|
| 场景/检查 | 1019/3381 | 同左 | 同左 |
| 失败 | 0 | 0 | 0 |
| 执行状态 | exit0 | exit0 | exit0 |
| 完整调用/状态输出 | 原行为 | 完全一致 | 完全一致 |

创建失败、foreign AlreadyCreated、启用排队失败、Apply失败及cleanup失败组合均保留原结果。
foreign目标不被删除；清理失败可能留下本轮对象，模型如实记录，不把零断言失败误读为零残留。
单hookInit的AlreadyInitialized返回规则、Enable失败后的Remove，以及Disable失败时不继续Remove都未改动。
成就兼容31/31、原版来源16/16、UI12/12包装器三态通过；不计为新的真实Steam/GUI验收。
Debug/Release、源码ZIP/DLL副本回滚和完整包重建通过，第三方MinHook无改动。

## 记录及范围

报告：`test/reports/20261014_hook_batch/`，含原始源码、三态trace、业务夹具、scope guard、构建和最终验证。
四角色继续复用 `test/reports/20261012_variable64_transaction/` 下的
`MODIFIED_FILE.zip`、`DIFF_FILE.patch`、`VERIFICATION.txt`、`ROLLBACK.sh`。
回滚脚本对 `*.hook-batch.zip`或 `*.hook-batch.dll`副本恢复本批基线，完整包另验证binary patch及最初基线回滚。

没有部署、进入游戏或实际patch；native线程/trampoline运行生命周期和服务端scheduler失败清理仍待进一步复核。
设计见[批量Hook启用与创建所有权](../../ai_docs/03_插件/批量Hook启用与创建所有权.md)。
