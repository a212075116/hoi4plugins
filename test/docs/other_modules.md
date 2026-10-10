# 其余模块测试脚本

> camera / console / effect / hook / crash_test 五个模块。
> 这些多为**探索期产物**，命名已按「模块 + 动词 + 名词」统一，
> 但**具体用途以文件内容为准**（下面只是简要说明）。规则见《README.md》。

## camera（对应 `SDK_RVA/camera/`）

| 文件 | 说明 |
|---|---|
| `camera_probe_1.js` | 摄像机对象探测（早期 `_cam_probe.js`） |
| `camera_probe_2.js` ~ `camera_probe_6.js` | 逐步深入的探测（早期 `_cam2.js` ~ `_cam6.js`） |

摄像机相关的**运行脚本**（`_cam*_run.py`）尚未迁入；当前活跃的用法是：

```
python -u modules/console/exec_command_run.py setcamheight 500
python -u modules/console/exec_command_run.py setcameraheight_lowerlimit 35
python -u modules/console/exec_command_run.py setcameraheight_upperlimit 3000
```

## console（对应 `SDK_RVA/console/`）

| 文件 | 说明 |
|---|---|
| `command_check.js` / `command_check_legacy.py` | 检查命令是否注册成功 |
| `command_list.py` / `command_list_run.py` | 列出控制台命令（`_exec_cmd.js` 里的 `listCmds`） |
| `exec_command_run.py` | **执行任意控制台命令**（最常用） |
| `command_range_run.py` | 按范围批量查命令 |
| `add_control.py` | 增加控制项（早期实验） |
| `control_syntax.py` / `control_probe_2.py` | 控制台语法探测 |

**最常用的一条**：

```
python -u modules/console/exec_command_run.py <命令名> [参数...]
```

## effect（对应 `SDK_RVA/effect/`）

| 文件 | 说明 |
|---|---|
| `effect_add_token.js` + `effect_add_token_run.py` | 注册 token（名字 ↔ id） |
| `effect_registry_probe.js` + `effect_registry_run.py` | 探测 Effect 注册表 |
| `effect_verify.js` + `effect_verify_run.py` | 验证注册结果 |
| `effect_dump_entry.js` + `effect_dump_entry_run.py` | dump 一个 Effect 表项 |
| `effect_map.js` + `effect_map_run.py` | 列出已注册的 Effect |
| `effect_add_token_run_2.py` | 注册流程的第二轮尝试 |

原理与结论见 `ai_docs/08_Effect系统/注册新Effect.md`。

## hook（对应 `SDK_RVA/hook/`）

| 文件 | 说明 |
|---|---|
| `hook_date_update.js` + `hook_date_update_run.py` | hook 日期同步函数，看参数 |
| `hook_date_format.js` + `hook_date_format_run.py` | **hook 日期格式化，抓调用链**（定位界面更新入口用的就是这个） |
| `hook_ui_entry.js` + `hook_ui_entry_run.py` | hook UI 更新入口，抓面板指针 |
| `hook_file_api.js` + `hook_file_api_run.py` | hook 文件 API（配合崩溃重定向） |
| `hook_probe.js` / `hook_probe_2.py` / `hook_probe_3.py` | 早期 hook 实验 |
| `probe_process.js` / `process_probe_run.py` / `process_probe_2.py` / `process_probe_3.py` | 进程创建相关探测 |
| `process_trace.ps1` | 进程追踪（PowerShell） |
| `file_redirect_test.py` | 崩溃文件重定向测试 |

**注意**：hook 相关脚本必须**关掉游戏再重开**才能干净复现，
而且**不要在同一进程里反复 connect/detach**（见 README 硬规则 2）。

## crash_test（对应 `SDK_RVA/crash_test/`）

| 文件 | 说明 |
|---|---|
| `crash_worker_thread.py` | 让工作线程解引用 NULL（等价于 `crashme` 命令） |
| `crash_calling_thread.py` | 让调用线程解引用 NULL（等价于 `crashme_main`） |
| `crash_directory_test.py` | 崩溃目录重定向测试 |
| `crash_string_analysis.py` / `crash_string_analysis_2.py` | 分析崩溃字符串 |

**更简单的用法**：直接在游戏控制台敲 `crashme` 或 `crashme_main`。

崩溃报告汇总工具在 `lib/crash_report.py`：

```
python -u lib/crash_report.py
```

## 相关文档

| 主题 | 文档 |
|---|---|
| 探针公共库与硬规则 | `test/docs/README.md` |
| 日期模块 | `test/docs/gamedate.md` |
| Effect 注册原理 | `ai_docs/08_Effect系统/注册新Effect.md` |
| hook 选型（IAT vs inline） | `ai_docs/05_工具链/MinHook集成与hook选型.md` |
| 崩溃文件重定向 | `ai_docs/05_工具链/崩溃文件重定向.md` |
