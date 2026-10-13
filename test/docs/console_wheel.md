# 外部控制台滚轮回归

2026-10-13。用户报告：只能拖动右侧滑条，鼠标滚轮不能上下滚动。

## 原因与修复

输入循环原先只处理按下的键盘事件，丢弃鼠标事件。
现在显式启用`ENABLE_MOUSE_INPUT`并处理`MOUSE_EVENT / MOUSE_WHEELED`，通过`SetConsoleWindowInfo`移动视口，不移动输入光标、不修改命令。
遵循Windows滚动行数设置，支持整页、小于120的增量累计和上下边界。
水平滚轮和其他鼠标事件不参与垂直滚动。

`Print`在光标位于视口下方时保存并恢复历史视口；在输入行可见时继续跟随输出。
键盘编辑仍回到输入行。不会增加日志队列或无限扩展原生屏幕缓冲区；缓冲区已被覆盖的历史无法恢复。
这不是任务栏归组修改，也不改变游戏命令入口、权限或多人判断。

## 可重复测试

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
