# 命令目录句柄所有权三态回归

2026-10-14，第十六批，Query内部RAII，公开接口不变。

## 执行

从项目根运行：

```powershell
python test/modules/console/test_catalog_handles.py SOURCE_ROOT OUTPUT
```

需要MSVC x64 C++17，源根含完整src；输出使用独立目录。
夹具包含真实 `command_catalog.cpp`，固定虚拟地址映射替代WinAPI进程/快照/内存调用，真实C++ operator new可定点抛bad_alloc。
35个场景覆盖进程/快照失败、模块缺失、PE指纹、表界限、名称/别名、SSO/长名称、读取失败、表变动、三次重试、本地slash及异常清理。

| 观察 | BASELINE | MODIFIED | ROLLBACK |
|---|---|---|---|
| 32个普通查询场景 | 返回/提示/读取/关闭摘要 | 完全相同 | 完全相同 |
| 三种异常后的资源残留 | process或process+snapshot | 无残留 | 恢复旧残留 |
| 总检查/失败 | 1061/3 | 1065/0 | 1061/3 |
| 执行状态 | exit1 | exit0 | exit1 |

修改版多四次检查来自实际执行的四次异常路径关闭，不是修改期望降低覆盖。
基线与回滚完整stdout一致；普通32场景每行记录三态一致，stderr均空，编译exit0。
异常在夹具边界捕获，仅用于记录；生产Query不新增catch。
真实分配失败场景与API替身异常分别标识，不把受控故障当作实机测试。

初版fixture错误地排列了SSO短名称与其长前缀的期望，导致额外两项测试失败；已修正为字典序。
`fixture_sort_error.json`保留该错误输出，修正后基线只剩三项真实资源清理失败。
console/log17项三态一致；实际构建客户端的 `--self-test`17/17和 `--completion-self-test`20/20三态输出一致，均不执行游戏指令。Debug/Release通过；源码ZIP及客户端EXE副本回滚恢复原始哈希，插件DLL未变。

## 记录

报告：`test/reports/20261014_catalog_handles/`。
持续复用 `test/reports/20261012_variable64_transaction/`四角色：
`MODIFIED_FILE.zip`、`DIFF_FILE.patch`、`VERIFICATION.txt`、`ROLLBACK.sh`。
回滚脚本对 `*.catalog-handles.zip`、`*.catalog-handles.exe`副本恢复本批基线，完整包另验证binary patch和最初基线回滚。
新客户端未部署，真实游戏进程、GUI、多人、全局pipe/线程和日志tail生命周期不是本批验收。
说明见[命令目录查询句柄所有权](../../ai_docs/05_工具链/命令目录查询句柄所有权.md)。
