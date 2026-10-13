# 外部调试控制台第一版测试入口

后续日志/输入/连接保护已更新，最新17/17自测及2701秒共享运行核观测见[抗压记录](console_stress.md)；下表14/14为首版历史结果，不当作当前自测输出。

2026-10-13，目标为本机HOI4 1.19.3 x64单人。实现与用户命令见[控制台使用说明](../../ai_docs/05_工具链/外部调试控制台可行性与接口方案.md)。
本页只记录自动验证，GUI排版/中文宽字符输入/关闭按钮体验另见[用户待办U04](用户尚未测试的待办事项.md)。

## 快速使用和诊断

2026-10-13权限策略更新：单人铁人允许外部指令，开发者分派不依赖`-debug`；多人独立拒绝，不沿用旧联合权限门。见[实现和验证边界](console_permission.md)。

从项目根运行；游戏启动后`-debug`自动弹出独立终端，`-no-plugin-console`关闭自动弹出。
也可运行游戏根目录的EXE。部署三个产物，不再只部署两个DLL。

```powershell
& '..\hoi4_debug_console.exe'
& '.\build\Release\hoi4_debug_console.exe' --self-test
& '.\build\Release\hoi4_debug_console.exe' --pid 你的游戏PID --command 'help setcamheight'
& '.\build\Release\hoi4_debug_console.exe' --pid 你的游戏PID --logs-ms 1200
```

`--command`输出真实transport/id/status/ok/thread与message；进程exit 0=原版成功，1=原版返回失败，2=连接或客户端失败，3=执行前拒绝/取消或原生故障。
`--logs-ms`以重定向stdout输出同一读取路径的三类日志，时间范围1..60000毫秒，不开交互窗口。
这些诊断模式不改变原版命令语义，也不会将命令当操作系统shell运行。

## 首版交付历史结果，分轮不相加

| 验证 | 已观察到的结果 |
|---|---|
| 增量Tail自测 | 14/14；缺文件、部分行、UTF-8跨块、无重复、截断/重建、截断迅速增长、大行、积压、限流与转义清理 |
| 真实地图/暂停命令、输入/协议/断线/权限分支、堆释放 | 29/29；其中240条8客户端并发全部返回 |
| 大结果释放 | 观察252个返回堆块释放，其中20个超过4KiB的对齐块；无待释放返回块 |
| 协议分片/连续与重复ID/不完整报文 | 4/4；分片正确拼接、同连接连续ID成功、重复ID断开、部分payload约5秒超时 |
| 端点冲突/服务PID校验 | 3/3；预占管道使插件拒绝启用，伪造服务被客户端拒绝，游戏进程存活 |
| 菜单取消 | 2/2；明确status=2，未调用游戏调度，不承诺菜单命令可用 |
| 独立进程生命周期/日志 | 6/6；debug自动单实例、重开幂等、终止helper游戏存活、重开、三个真实来源、游戏退出helper跟随退出 |
| 摄像机旧动画回写 | 旧版本3次均错误回到500；修复后三次均保持950.25 |
| 摄像机既有共享路径回归 | 9/9；原版setter与Effect所列高度/上下限路径、参数不改写与fixture无错误 |

权限拒绝通过临时替换原版调度谓词进行故障注入，不是真实多人或Ironman战役测试。
生命周期采用进程终止验证隔离，不是假称点击过窗口X按钮。
原版入口包装层保留`CmdManager+220`计数，两次请求观测到增量2；不是仅绕过包装层调用handler。
暂停通过`gamespeed 0`及测试前后raw date一致确认，不以“窗口仍开着”替代。
冻结游戏执行线程5秒时请求取消，恢复后高度保持500，证明不会迟到执行1234。
并发测试是有界功能压力，不声称多小时或超过2GB内存压力验收。

## 可重复执行脚本

输出路径均为`test/reports/20261012_variable64_transaction/external_console/`，阶段名必须新建，已有记录拒绝覆盖。
完整运行需要现有bakaifa测试mod、a64soak继续存档、以及`zzc.1`摄像机fixture；不是任意用户环境开箱即可运行的驱动。
fixture由`test/modules/camera/verify_camera_effect_shared.py`生成，事件只设置高度并写CAMSHARED日志；运行会重启游戏，不应拿正式战役执行。

```powershell
python test/modules/camera/verify_camera_effect_shared.py YOUR_NEW_CAMERA_PHASE
python -c "import sys; sys.path.insert(0,'test/tools'); import hoi4_launch as H; H.launch(['-gdpr-compliant','-nolauncher','-debug','-continuelastsave'],wait_marker='[plugin] Camera_RegisterCommands',timeout=240)"
python test/modules/console/verify_external_console.py YOUR_NEW_PHASE --stress
python test/modules/console/verify_camera_command_race.py YOUR_NEW_PHASE
```

等待Camera命令注册和地图恢复完成再执行，不把启动早期的“取消”误当功能通过。
`verify_camera_command_race.py PHASE --native`用于无桥接旧DLL的诊断三状态，直接调用已有测试RPC；不作为生产线程调度实现。
`verify_external_console.py PHASE --menu`仅用于无继续存档的菜单进程，验证安全取消。
`verify_external_console_collision.py`会启动一个受控挂起进程并预占管道，只验证本机冲突，不作远程攻击测试；`verify_external_console_stream.py`测试分片/重复ID/不完整报文。
`verify_external_console_lifecycle.py [NEW_PHASE]`会终止helper并最终退出游戏，测试输出存在时拒绝覆盖；不能在有其他同名helper的多游戏环境随意执行。

## 三状态与回滚

同一客户端输入`setcamheight 500`：BASELINE旧DLL连接失败exit=2；MODIFIED有真实ok=1、height=500、游戏线程ID，exit=0；ROLLBACK恢复旧DLL后再次连接失败exit=2。
恢复DLL的SHA256与本轮原始DLL`959aab27d536af1a302f3a3db8575e660eae41b87f5209a0d07f135bb1143e5f`一致，再重新部署本轮MODIFIED，不能把生产留在回滚态。
快速镜头原生诊断输入同为`setcamheight 500`、再次同值设置、`event zzc.1`；BASELINE/ROLLBACK均0/3、MODIFIED3/3。

继续复用`test/reports/20261012_variable64_transaction/`下四个角色：`MODIFIED_FILE.zip`、`DIFF_FILE.patch`、`VERIFICATION.txt`、`ROLLBACK.sh`。
追加本轮SOURCE_BASELINE、原DLL和审计脚本基线，不丢弃前期记录；patch需精确重建包，rollback需精确恢复基线。
ROLLBACK接收副本：`*.external-console.dll`恢复本轮原DLL，`*.external-console.source.zip`恢复本轮源码/文档快照，`*.external-console.policy.py`恢复旧策略审计脚本。
不要在游戏运行时直接覆盖已加载DLL；脚本只恢复指定副本，不自动删除生产目录或回退Git。

## 证据 → 结论 → 下一条路径

- `modified_ready_final.json`：请求stdout/stderr/exit、线程、权限拒绝、超时取消、并发和释放见证 → 桥接不是只打印模拟成功 → 仅剩列明的GUI主观交互。
- `menu_final.json`与`rollback.json`：未执行分支明确、安全恢复原DLL → 不把菜单取消或旧DLL失败写成功 → 未覆盖的新版本/真实多人需专项测试。
- `baseline_native_camera_race.json`、`modified_native_camera_race.json`、`rollback_native_camera_race.json`：相同输入的旧动画竞态与修复 → 参数快照/取消机制可复现 → 更多快速上下限组合和视觉过渡另测。
- 原生异常分支仅做保护性实现，未故意让游戏实际原生崩溃验收；远程客户端拒绝为代码/API约束，本轮没有联网远端实测。
- 初次编译、Frida短谓词拦截、别名诊断夹具和旧动画失败原文保留，不算最终通过；仅改正命令/机制后产生的记录作为通过依据。
## 滚轮修复补充

2026-10-13首轮鼠标事件/视口方案被用户确认无效；当前显式关闭鼠标接管，由宿主管理历史滚动。真实ConPTY路由检查通过，但物理滚轮尚未确认；[完整更正与验证边界](console_wheel.md)，真实体验由U04确认。
