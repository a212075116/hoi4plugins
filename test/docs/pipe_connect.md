# 连接与传输收尾三态

2026-10-14，第二十五批。

## 入口

```powershell
python test/modules/console/test_pipe_connect.py SOURCE_ROOT OUTPUT
python test/modules/console/test_pipe_connect.py SOURCE_ROOT OUTPUT --real
```

旧源码提取实际Peer的连接块，新源码调用实际DcConnect；两者包含实际protocol.h。
故障矩阵使用受控Win32返回值，断言事件关闭前已无pending操作、无无效关闭；传输覆盖读/写和带/不带取消事件。
Peer调用点另核对仅连接前缀变化，游戏权限和后续队列字节保留。

| 故障矩阵 | BASELINE | MODIFIED | ROLLBACK |
|---|---:|---:|---:|
| 连接/传输输入 | 1000/2000 | 同左 | 同左 |
| 检查数 | 33400 | 33800 | 33400 |
| 新生命周期断言失败 | 1700 | 0 | 1700 |
| 退出码 | 1 | 0 | 1 |

同输入hash一致；执行分支变化使断言数不同，不声称修改版完整stdout与基线相同。
恢复版完整stdout与基线相同；独立源码包/DLL/helper副本由ROLLBACK.sh恢复，哈希相同。

## 真实传输与回归

三态各64轮真实本机Win32管道交换：32预连接、32延迟连接，PING/PONG内容验证，1120检查、0失败、exit0。
真实线程检查计数使用Interlocked，退出后拥有的句柄数恢复；不调用游戏/Steam。
console17三态、当前启动67场景/8425检查、门闩512轮/6628检查继续通过，Release/Debug构建通过。
独立CHI实际修改版/恢复版就绪及变量大数→原版2.5另有日志；最终重新部署修改版DLL和helper，不覆盖正式存档。

## 错误记录与边界

首次夹具模板使用普通CONNECT占位符，误替换ERROR_PIPE_CONNECTED，编译C2065/C2143、exit2；改为独立@@标记后重新执行，原错误JSON保留。
一次构建驱动最后的helper进程查询返回exit1，编译阶段已通过；随后改为显式计数查询，不把进程不存在误判为构建失败。
取消是请求而非同步完成，不仅调用CancelIoEx就释放OVERLAPPED；有效拥有句柄的收尾可等待，不能承诺所有驱动故障下仍固定期限返回。
失败连接的50ms退避是实际代码分支，故障夹具不代表真实OS资源耗尽或GUI效果。
间歇退出按用户要求暂缓，本批不宣称其根因或解决结果。

## 证据

报告 `test/reports/20261014_pipe_connect/` 保留输入hash、实际命令、stdout/stderr、退出码、三态与实机结果。
仍复用 `test/reports/20261012_variable64_transaction/` 的四角色：
`MODIFIED_FILE.zip`、`DIFF_FILE.patch`、`VERIFICATION.txt`、`ROLLBACK.sh`。
本批副本后缀 `*.pipe-connect.zip`、`*.pipe-connect.dll`、`*.pipe-connect.exe` 恢复本批原始字节。
设计见[异步连接与传输收尾](../../ai_docs/05_工具链/异步连接与传输收尾.md)。
