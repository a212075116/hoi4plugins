# 第一批源码简化回归

2026-10-13。验证公共日志合并、控制台字符串复用、候选查询拆分及废弃help解析器移除。
不执行游戏指令、不推进游戏时间、不触发成就；不更改正在运行的游戏DLL。

## 日志与字符串三态

从项目根执行；PowerShell下的源目录使用本机实际路径：

```powershell
python test/modules/console/run_source_refactor_regression.py --output test/reports/20261013_source_refactor --phase MODIFIED
```

需要本机VS2022 Community原生编译器，脚本不启动游戏。
通过 `--source-root` 可对同目录布局的原始/恢复源码运行同一套输入。
夹具包含真实 `console_cmd.c`，提取真实 `Plugin_Log` 函数体，并在存在时包含真实公共日志实现。
原生assign与文件/时间调用被确定性模型替代；内存可读检查使用实际Win32查询。
这不是游戏内原生分配器或磁盘耐久性验收。

BASELINE、MODIFIED、ROLLBACK均17/17、exit0，stdout完全相同、stderr为空。
覆盖15/16字节SSO转换、空值、零容量保留ok、无模块截断、参数范围、日志路径/时间戳/CRLF、追加共享/关闭、2047/2048字节边界。
保留第一次夹具断言的长度误算记录；修正的是期望值，不是为了通过测试改变生产日志格式。

## 外部控制台

- 三态运行 `--self-test`：17/17、exit0，日志与队列行为一致。
- 三态运行 `--completion-self-test`：20/20、exit0；新版测试直接覆盖当前候选匹配逻辑，不再测试废弃help解析。
- 相同前缀查询与失败输入逐项比较stdout/stderr/exit。
- 实际 `PumpCompletion` 夹具复核输入替换、参数保留、过期拒绝、错误及长度限制。
- 日志配色：模型和真实ConPTY属性回归；滚轮：视口模型和真实ConPTY启动模式回归。
- 大文件日志夹具比较90000行输出，不使用游戏日志作为负载来源。

```powershell
python test/modules/console/run_color_regression.py REFACTOR_MODIFIED
python test/modules/console/run_wheel_regression.py REFACTOR_MODIFIED
python test/modules/console/run_host_wheel_regression.py REFACTOR_MODIFIED
```

直接包含 `main.cpp` 的历史夹具，现在同时包含 `command_catalog.cpp` 以补齐链接依赖；旧版单文件源码仍可运行。
GUI主观显示沿用上轮用户验收，本轮没有新的物理键盘、滚轮或截图验收。

## 构建、恢复与记录

Debug|x64、Release|x64完整解决方案构建通过。
拆分时发现的Toolhelp头文件遗漏与夹具carrier包含路径遗漏已修复，失败记录保留。
对修改版源码zip、helper、DLL的独立副本运行原事务 `ROLLBACK.sh`，恢复后的字节/哈希与本轮原始备份一致。
修改版源码与产物保留，不用回滚副本覆盖项目。

本轮新产物在 `build/Release/`，未覆盖游戏根部署文件。
`CURRENT_BUILD.json` 继续记录已部署版本；本轮构建哈希另存本轮报告，不能将两者混为一谈。
报告目录：`test/reports/20261013_source_refactor/`。
四个正式角色继续使用 `test/reports/20261012_variable64_transaction/` 下的MODIFIED_FILE.zip、DIFF_FILE.patch、VERIFICATION.txt和ROLLBACK.sh。
