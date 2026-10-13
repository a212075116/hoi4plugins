# 外部控制台滚轮回归

2026-10-13。用户报告：只能拖动右侧滑条，鼠标滚轮不能上下滚动。

## 当前结论：首轮方案未解决真实问题

用户在首轮部署后确认仍无法滚轮滚动。下面17项结果只证明模拟视口与事件算法，不能据此称真实问题已解决。
第二轮将启动输入模式中的`ENABLE_MOUSE_INPUT`显式清除，让终端宿主管理滚轮与历史；不强制开启Quick Edit，仍保留逐键命令编辑。
旧`ScrollConsole`仅保留为残余鼠标记录的兼容处理，不再作为当前历史滚动机制。

微软ConPTY模式转换源码在鼠标接管且Quick Edit关闭时启用VT鼠标报告；终端收到鼠标报告请求时，滚轮优先送给程序而非本地历史。
Windows Terminal的历史由宿主拥有，`GetConsoleScreenBufferInfo`不完整暴露历史，因此首轮`SetConsoleWindowInfo`方案不能当作通用实现。
参考：[模式转换](https://github.com/microsoft/terminal/blob/main/src/host/getset.cpp)、[滚轮路由](https://github.com/microsoft/terminal/blob/main/src/cascadia/TerminalControl/ControlInteractivity.cpp)、[兼容性记录及后续更正](https://github.com/microsoft/terminal/issues/10191)、[API限制](https://learn.microsoft.com/en-us/windows/console/setconsolewindowinfo)。

当前回归命令：

```powershell
python test/modules/console/run_host_wheel_regression.py MODIFIED
```

使用真实`CreatePseudoConsole`、子进程`CONIN$`和`Get/SetConsoleMode`，采用生产启动表达式；不注入真实鼠标事件。

| 当前三态 | 输入模式检查 | ConPTY鼠标报告 | 退出码 |
|---|---|---|---|
| BASELINE：首轮EXE对应源码 | 3/5，模式440仍接管鼠标 | 发出`CSI ?1003;1006h` | 1 |
| MODIFIED：宿主管理滚轮 | 5/5，模式424不接管鼠标 | 不发出上述启用序列 | 0 |
| ROLLBACK：恢复首轮源码 | 3/5，与BASELINE相同 | 重新发出启用序列 | 1 |

检查涵盖原生模式读写、键盘原始输入、Quick Edit关闭、窗口事件及256种继承模式；另检查实际ConPTY输出流。
证据保存在`test/reports/20261012_variable64_transaction/console_wheel_host/`。原始命令、输出和错误尝试均保留。
回滚恢复本轮基线源码SHA-256：`b1ae7a23f07aaa530139f073afaf3e49388aef370e1e84c6c087af8799908309`。
这是输入路由修正与真实ConPTY接口验证，仍不等于Windows Terminal/Console Host的物理滚轮及视觉验收；用户确认前保持未解决验收状态。
后台观看历史的跟随策略由宿主实现决定，不能用旧模拟测试承诺所有宿主都不拉回底部。

## 首轮历史实现与模型结果（已被用户否定真实效果）

输入循环原先只处理按下的键盘事件，丢弃鼠标事件。
现在显式启用`ENABLE_MOUSE_INPUT`并处理`MOUSE_EVENT / MOUSE_WHEELED`，通过`SetConsoleWindowInfo`移动视口，不移动输入光标、不修改命令。
遵循Windows滚动行数设置，支持整页、小于120的增量累计和上下边界。
水平滚轮和其他鼠标事件不参与垂直滚动。

`Print`在光标位于视口下方时保存并恢复历史视口；在输入行可见时继续跟随输出。
键盘编辑仍回到输入行。不会增加日志队列或无限扩展原生屏幕缓冲区；缓冲区已被覆盖的历史无法恢复。
这不是任务栏归组修改，也不改变游戏命令入口、权限或多人判断。

## 首轮模型测试（不是当前验收入口）

在项目根目录执行：

```powershell
python test/modules/console/run_wheel_regression.py MODIFIED
```

夹具从实际输入循环提取键盘过滤前的分支，并包含真实`main.cpp`与`Print`；Win32视口、输出和系统参数接口用确定性模型替代。
这能复现事件丢弃和后台日志拉回视口，但不等于物理鼠标或真实Console Host视觉认证。

| 状态 | 相同17项测试 | 退出码 |
|---|---|---|
| BASELINE | 11/17，上移、累计、分页、边界上移、历史保持失败 | 1 |
| MODIFIED | 17/17，包含100000次滚轮边界检查 | 0 |
| ROLLBACK | 11/17，与BASELINE逐字相同 | 1 |

原始命令、stdout、stderr、退出码和哈希保存在`test/reports/20261012_variable64_transaction/console_wheel/{BASELINE,MODIFIED,ROLLBACK}.json`。
回滚恢复源文件原SHA-256：`828ade859216f7e85e75f197e33c5edbf22aa09b3478c8f0b606cf4e6e66f199`。
真实滚轮、持续刷日志时观看历史、窗口调整后的体验仍见[U04](用户尚未测试的待办事项.md)。

相关：[外部控制台](external_console.md)、[抗压结果](console_stress.md)。
