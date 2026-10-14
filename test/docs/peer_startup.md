# Peer线程启动与故障状态回归

2026-10-14，第二十四批。

## 入口

```powershell
python test/modules/console/test_service_scheduler.py SOURCE_ROOT OUTPUT
python test/modules/console/test_peer_startup.py SOURCE_ROOT OUTPUT
```

第一个夹具提取实际服务启动、清理、门闩和hook adapter，外部资源API受控；第二个编译实际门闩/线程创建/服务入口，使用真实Win32线程及句柄，仅Peer主体受控。
真实线程测试的检查计数使用Interlocked，避免并发断言自身发生数据竞争。

## 同输入三态

| 实际启动夹具 | BASELINE | MODIFIED | ROLLBACK |
|---|---:|---:|---:|
| 场景数 | 67 | 67 | 67 |
| 检查数 | 8218 | 8425 | 8218 |
| 新合同断言失败 | 240 | 0 | 240 |
| 退出码 | 1 | 0 | 1 |

执行路径不同导致检查次数不同，输入场景相同；不宣称三个stdout完全相同。
BASELINE/ROLLBACK完整stdout相同，源码/DLL副本恢复哈希与基线相同。
新版在每个Peer失败位置均不进入ready，等待已创建线程结束后释放资源；成功才放行5个Peer。
既有console17回归三态通过，Release/Debug构建通过。

## 真实线程专项

32个创建失败掩码各执行16轮，共512轮；实际线程包装函数读取原子启动状态。
另测实际DebugConsole_Start的初始线程创建失败及禁止重试。
6628检查、0失败、exit0；门闩提交前/失败后无Peer调用，成功后5个调用，进程句柄数恢复原值。
旧源码没有门闩函数，不能伪造“旧版也运行这项专项”；旧错误由三态启动夹具证明。
没有TerminateThread、进程kill或对正式存档的操作。

## 实机与归档

独立 `-start_tag=CHI`，正常关闭后部署，实机就绪和变量大数→原版2.5语义分别记录，不只看transport。
PID、实际加载路径、命令和原始日志以报告 `test/reports/20261014_peer_startup/` 为准。
最终重新应用修改版，既有存档哈希核对不变；不把正常启动当作真实系统OOM故障注入。

仍使用 `test/reports/20261012_variable64_transaction/` 的四角色：
`MODIFIED_FILE.zip`、`DIFF_FILE.patch`、`VERIFICATION.txt`、`ROLLBACK.sh`。
本批副本回滚后缀 `*.peer-startup.zip`、`*.peer-startup.dll`，恢复本批基线字节。
设计见[Peer启动门闩](../../ai_docs/05_工具链/Peer线程启动门闩.md)。
