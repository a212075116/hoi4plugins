# 日志真实值三态回归

2026-10-14，第二十二批。

## 原生入口

```powershell
python test/modules/effect/test_var64_log_reader.py SOURCE_FILE OUTPUT
```

MSVC x64，源文件为variable64.c，输出独立目录。
直接提取实际DoLog/LoadSplit/ReadTrueRaw和格式化，原生scope/debt解析依赖受控；独立Python整数/文本oracle。

| 观察 | BASELINE | MODIFIED | ROLLBACK |
|---|---|---|---|
| 语料/检查 | 6000/18002 | 同左 | 同左 |
| marked 2000项失败 | 0 | 0 | 0 |
| 全部断言失败 | 8000 | 0 | 8000 |
| 执行状态 | exit1 | exit0 | exit1 |
| 变量/debt模拟数据 | 无写入 | 无写入 | 无写入 |

原native基线与回滚完整stdout一致；resolve失败返回/提示保留，marked格式/整数bits兼容。
registration27268、stored2049、decode21304、日期/Array64/Bool/typed/摄像机/console既有回归三态通过。
名称字段fixture原stub只提供返回式安装，语言模块引用Into导致LNK2019、exit2；已补受控Into并保留 `fixture_old_install_stub_error.json`，生产代码不是为此改动。
其他数值身份/算术/语言/ROOT/debt/text/name及生命周期检查重新通过。

## 实机与不计通过的记录

基线PID68428、新版PID63484离散流程均看到marked值12345678901.125；新日志在vanilla设置后为2.5。
旧DLL第一次离散回滚PID63528虽有transport成功，却没有vanilla回收观察，重复marked日志，保存为失败语义记录，不将其当作预期1的通过。
同一个编译effect组：新版PID64024日志2.5、旧回滚PID67396日志1，语言两组2.5；轮询实际进展而非只看ok字段。
对应命令、退出状态、PID分段日志、grouped游戏日志和错误记录全部保留。根因未归因，不宣称日志改动解决了离散RPC问题。
最终新DLL重新部署，独立CHI；不保存正式局、不用Frida spawn或timer kill，40既有save哈希保持。

## 归档

报告：`test/reports/20261014_var64_log_reader/`。
四角色继续复用 `test/reports/20261012_variable64_transaction/` 下的
`MODIFIED_FILE.zip`、`DIFF_FILE.patch`、`VERIFICATION.txt`、`ROLLBACK.sh`。
脚本对 `*.var64-log.zip`/`*.var64-log.dll`恢复本批源码/build基线；live旧DLL精确保存/恢复单列。
不把受控依赖、grouped比较或源文件hash当作完整并发/所有脚本路径证明。
设计见[日志复用真实值读取](../../ai_docs/09_脚本数值系统/日志复用真实值读取.md)。
