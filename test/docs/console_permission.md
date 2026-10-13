# 外部控制台单人权限策略

2026-10-13：用户要求单人铁人允许外部指令，开发者指令不依赖`-debug`或开发者启动模式；多人仍禁用。

## 实现

`DispatchExternal`先独立调用manager+144的原版网络谓词；它检测`CNetworkServer`/`CProxyServer`。
网络状态成立就以DC_REJECTED拒绝，原版调度与命令handler均不调用。谓词不可读取也拒绝；原生异常仍禁用整个桥接。
单人路径保持原manager身份，在已有游戏线程执行边界内原子交换+80权限选择器，临时使用返回false的原生谓词，进入原版0x24B4D40/0x24B4D60。
原版总拒绝为P80&&(P208||P144)，开发者分派也依赖P80；P208读取gamestate+0xC0低位。
仅在同步外部请求中解除分派限制，不修改真实铁人位、全局启动参数或原版命令条目的权限，不永久放开内置控制台。
`__finally`恢复+80选择器及manager+216/217原版UI标志；正常返回和异常均恢复。+220原版调用计数保留正常递增，结果仅发送给外部窗口。
命令自身额外的状态/参数要求不被统一移除；“放开开发者指令”指查表分派权限，不保证每个命令在任意游戏状态下都成功。
不承诺使用指令后成就仍有效，不测试危险崩溃、删除、退出或破坏存档命令。

## 自动矩阵

```powershell
python test/modules/console/run_permission_regression.py MODIFIED
```

同一16种输入：多人/单人、铁人/非铁人、开发者/普通、开发者命令/普通命令，各两值组合。
使用真实`DispatchExternal`源码与受控原生调度替身；不是实际联机或真实铁人存档。

| 三态 | 当前要求通过数 | 退出码 |
|---|---|---|
| BASELINE旧策略 | 5/16 | 1 |
| MODIFIED | 16/16 | 0 |
| ROLLBACK | 5/16，输出与基线一致 | 1 |

每项检查handler调用、接受/拒绝、manager谓词指针保持与原版调用计数。
另通过UI标志恢复及注入原生异常后的权限指针恢复测试。
证据：`test/reports/20261012_variable64_transaction/console_permission/`，包含旧源码、旧DLL、三态命令与输出、二进制谓词证据。
## 实机验证

Steam启动后，在不带`-debug`的真实单人铁人存档中完成6/6原生测试；铁人位前后均为true。
`debug_dumpdiploactions`注册标记为开发者专用（RVA0x9D55写入entryStateFlag=0）：旧开发者门返回`Command available only for developers.`，新外部路径返回`Dumped diplo actions`，exit=0。
为了独立测试开发者门，旧路径回放仅在同步原版调用期间调整选择器，返回前恢复；真实铁人位与原谓词对象虚表不修改。
铁人门单独回放时，旧路径拒绝`help setcamheight`，新路径成功返回帮助。
网络/网络+铁人两种谓词注入均返回`External console commands are disabled in multiplayer.`，DC_REJECTED/exit=3，原版分派调用数不增加。
这是实际铁人存档和原版命令分派验证；网络是谓词注入，不是真实多人联机。
另做不附加Frida的100次只读帮助请求、测试脱离后的100次查询和60秒存活观察，全部通过；不执行改数值、保存、退出或崩溃指令。

首次PID42148的6项请求因无执行上下文全部取消，记录保留为`native_unavailable_context.json`；不算权限测试通过。
早期版本曾在实机查询后退出，捕获C0000005；不把“6项返回正确”当作稳定性通过。
即使无Frida且脱离Job仍复现；三个崩溃dump一致落在原版RVA0xB1B0E9，读取NULL+0x58，栈经Frame的原版更新调用。
旧DLL无指令对照120秒仍存活；新路径仅恢复权限选择器仍会失败，补充恢复原版UI标志后同存档100+100请求与60秒观察通过。
对照定位到外部执行结果不应污染原版控制台UI状态；保留失败版、错误请求、崩溃摘要与对照记录，不宣称所有原版崩溃均已解决。
启动器未使用Frida spawn；测试脚本无游戏倒数kill。执行宿主Job的LimitFlags=0x2800确有KillOnJobClose，但这不是已确认的上述崩溃原因。
`launch_detached_console_session.py`通过Explorer父进程继承启动，已实测游戏in_job=false；持续保活启动器保留为诊断，不作当前首选。
旧通用`hoi4_launch.py`启动/部署会主动结束旧游戏，本轮没有调用它。
Frida仅attach；最终夹具不替换原对象虚表、不分配NativeCallback，只在同步分派中回放选择器与注入网络谓词返回值，返回时恢复再detach。
测试前备份最新7份存档；最终7/7哈希未变化。备份与后续复核证据保存在同一报告目录。
相关：[外部控制台](external_console.md)、[用户待办](用户尚未测试的待办事项.md)。
