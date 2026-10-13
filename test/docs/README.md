# 测试脚本总览（test/）

> 本目录是**探针与测试脚本**。改插件前先看这里，不要凭记忆写新脚本。
> 测试报告放 `test/reports/`，技术结论写 `ai_docs/`。
> 核对：2026-10-13；命令默认从hoi4plugins项目根执行。

## 目录结构

| 目录 | 用途 |
|---|---|
| `docs/` | **本目录**，说明每个脚本怎么用、能干啥 |
| `lib/` | **公共库，只放稳定复用的东西**（见下表）。新增探针不要放这里 |
| `modules/<模块名>/` | 按模块归类的探针与运行脚本，**活跃脚本都在这里** |
| `tools/` | 启动/部署等**工具**（`hoi4_launch.py` 等）。历史一次性脚本也在 `.py` 里，靠 `_` 前缀区分 |
| `archive/`、`probes_*` | 历史一次性探针，不再维护 |
| `reports/` | 测试报告、截图、CE 表 |

## 公共库（`lib/`）

| 文件 | 作用 |
|---|---|
| `frida_host.py` | Frida 宿主：`find_pid` / `in_game` / `wait_in_game` / `connect` / `detach` |
| `exec_console_command.js` | **最常用的探针**：进程内执行控制台命令 `exec(命令, 参数[])` |
| `idalib_cli.py` | 向 idalib 常驻服务发查询（decompile / disasm / xrefs_to / strings / names / vtable） |
| `idalib_server.py` | idalib 常驻服务本体（TCP 127.0.0.1:19531） |
| `probe_common.py` | 探针公共小工具 |
| `crash_report.py` | 崩溃目录分析 |

`lib/` 里的路径是写死的，所有脚本都引用它 —— **移动它会连带大量脚本失效**。

## 模块目录

| 模块 | 对应源码 |
|---|---|
| `modules/gamedate/` | `SDK_RVA/gamedate/`（日期读写、界面刷新） |
| `modules/camera/` | `SDK_RVA/camera/`（摄像机高度） |
| `modules/console/` | `SDK_RVA/console/`（控制台指令注册；[外部控制台 Tab 补全](console_completion.md)） |
| `modules/achievement/` | `SDK_RVA/achievement/`（[阶段记录](achievement_compat.md)、[真实解锁](achievement_eligibility.md)、[前端图标](achievement_ui.md)，更多平台/模式覆盖待扩展） |
| `modules/effect/` | Effect注册、scalar64与Array64阶段测试 |
| `modules/trigger/` | Bool/typed注册、比较、原生tooltip与动态/数组隔离 |
| `modules/hook/` | `SDK_RVA/hook/`（文件重定向、进程拦截、inline hook） |
| `modules/crash_test/` | `SDK_RVA/crash_test/`（崩溃测试命令） |

---

源码规范化回归见[第一批源码简化](source_refactor.md)：同输入比较旧版、新版和回滚版，不执行游戏指令。

## 正确的测试流程（照这个做，不要自创）

### 方式 A：用 `tools/hoi4_launch.py`（推荐，永不盲等）

它把「杀旧进程 → 清插件日志 → 部署 → 启动 → 按标记轮询等待」全包了。

```python
import sys
ROOT = r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
sys.path.insert(0, ROOT + '/hoi4plugins/test/tools')
import hoi4_launch as HL

HL.deploy()                                   # 杀游戏 + 复制载体、插件及外部控制台三个产物
dt, _ = HL.launch(args=['-gdpr-compliant', '-start_tag=ABY', '-nolauncher', '-force_text_save'],
                  wait_marker='[plugin] Camera_RegisterCommands',   # 到达命令注册阶段；还需检查各模块成功数
                  timeout=200)
print('plugin ready in %.2fs' % dt)
```

| 函数 | 作用 |
|---|---|
| `deploy()` | 先杀 hoi4，再复制 `build/Release/` 的 `tbb.dll` 与 `hoi4_mod_plugin.dll` 到游戏根 |
| `launch(args, wait_marker, timeout)` | 杀旧进程 → 清日志 → `Popen` 启动 → **按标记轮询**等待 |
| `build_and_launch(marker, timeout, args, skip_build)` | 上面两步合一 |
| `wait_for(marker, timeout, poll)` | 轮询插件日志；**进程死掉会立刻抛错**，不会静默超时 |
| `status()` | 回显最近的 `[eff]` / `[plugin]` / `[scan]` 行 |

可用就绪标记：

| 标记 | 含义 | 实测耗时 |
|---|---|---|
| `[eff] camera height effect ready` | effect 可注册 | 约 3.5 秒 |
| `[plugin] Camera_RegisterCommands` | 摄像机命令注册阶段；不是全部功能成功/进地图保证 | 历史机器约14.4秒，非超时依据 |

### 方式 B：手动 `Start-Process`（方式 A 不适用时）

```
# 1) 游戏必须先用 Start-Process 独立启动（绝不能 frida.spawn）
Start-Process -FilePath '<游戏根>/hoi4.exe' `
  -ArgumentList '-gdpr-compliant -start_tag=ABY -nolauncher -force_text_save' `
  -WorkingDirectory '<游戏根>'

# 2) 轮询等进图（判据是 game.log 里的 Launching SINGLEPLAYER-game，不要盲等固定秒数）
#    进图后再等 30 秒以上，让游戏初始化稳定

# 3) 跑脚本
python -u test/modules/<模块>/<脚本>.py [参数]
```

### 常用现成脚本（不要重造）

| 脚本 | 用途 |
|---|---|
| `modules/console/numtest_trigger_events.py` | **触发 mod 事件**：`python -u ... zzdatetest.97 zzdatetest.96` |
| `modules/console/numtest_run_command.py` | 执行单条控制台命令 |

触发后看结果：

```
Get-Content '<文档目录>/Paradox Interactive/Hearts of Iron IV/logs/game.log' -Tail 60 |
  Select-String -Pattern '关键字'
```

---

## 三条硬规则（都踩过，代价很大）

**1. 不要用 `frida.spawn`**

spawn 出来的游戏进程会随宿主 Python 进程结束被一起终止，现象是「一跑完脚本游戏就没了」，
**会被误判成崩溃**（无 dump、无事件日志）。标准做法：外部 `Start-Process` 启动，
外部启动并确认find_pid非空后再connect(force_spawn=False)。该参数只禁止“强制重开”，没有进程时connect仍会自动spawn；不能把它当绝对禁止spawn。

**2. 不要无控制地快速反复 connect/detach**

历史曾在快速反复开关会话时死亡；优先单会话复用并在finally收尾。已有分阶段驱动按其生命周期管理会话，不能据此声称所有重复attach必然崩溃。
需要同时用多个探针时，在那个 JS 探针里多写几个 rpc 方法，而不是开两个会话。

**3. `auto_unpause` 是开关，不是「取消暂停」**

每调一次在开/关之间切换，**必须看返回值确认状态**。

## 其它容易忘的点

- 游戏进图后**默认暂停**，日期不推进；要 `auto_unpause <1..5>` 才会走
- **游戏刚进图的头 ~30 秒内写入会被它自己重置**，必须等稳定再写
- `CGameState`（`*(hoi4.exe+0x332F260)`）非 NULL ≠ 已进图，主菜单也可能非 NULL；
  判据是 `game.log` 里的 `Launching SINGLEPLAYER-game`
- 编译前**先杀游戏**，否则 `LNK1201`（pdb 被占用）
- 部署要**同时覆盖 `tbb.dll` 和 `hoi4_mod_plugin.dll`**，且杀游戏后等几秒再复制
- 部署后比较构建/游戏根DLL的SHA-256及注册日志；仅时间戳不足以保证版本。单独构建vcxproj须指定SolutionDir，见ai_docs构建说明

## 新增脚本放哪里

| 类型 | 位置 | 命名 |
|---|---|---|
| 探针（JS，`rpc.exports`） | `modules/<模块>/` | `<动词><名词>.js` |
| 运行脚本（Python） | `modules/<模块>/` | `<动词><名词>.py` |
| 稳定公共库 | `lib/` | 见上表 |
| 启动/构建工具 | `tools/` | 不带下划线前缀 |

**不要往 `lib/` 塞一次性探针，也不要往 `tools/` 塞一次性脚本。**
名字要能望文生义，不要出现 `_a2.js`、`_chk3.py` 这类只能靠记忆的名字。

## 历史目录（探索期产物，不再维护）

| 目录 | 内容 |
|---|---|
| `probes_js/` | 早期 JS 探针（活跃的已移入 `modules/`） |
| `probes_frida/` | 早期 Python 宿主脚本 |
| `tools/_*.py` | 早期一次性运行脚本（带下划线前缀的那些） |
| `probes_ida/` `probes_idalib/` `probes_py/` | 早期 IDA 批处理与纯 Python 脚本 |
| `jobs/` | 早期后台任务产物 |

**要用某个历史脚本时**：先在 `reports/` 或 `ai_docs/` 里搜它对应的结论，
再决定是否值得翻出来；**不要直接照着它的名字猜用途**。

## variable64 固定种子抗压入口（2026-10-12）

- `modules/effect/stress_variable64.py PHASE --extended`：516 项断言，含重启读档、跨国家同名、2560 次交替运算、192 个变量、70 笔同时挂账、边界与 clear。必须先构建；该脚本部署构建产物并重启游戏。PHASE 使用新名字，旧报告不覆盖。
- `modules/effect/test_var64_identity.py SOURCE OUTPUT_DIR`：从 SOURCE 提取实际身份/查表函数，原生夹具 8 项。
- `modules/effect/test_var64_raw_math.py SOURCE OUTPUT_DIR`：实际限幅函数与 Python 整数 oracle 对比 10676 组输入。
- `modules/effect/test_var64_language_name.py SOURCE OUTPUT_DIR`：语言桥接名字布局 6 项。

原生夹具依赖本机 VS x64 编译环境。详细边界、性能开销和证据见 `ai_docs/09_脚本数值系统/读档身份与抗压验证.md`。

## Trigger 注册器入口（2026-10-12）

- `modules/trigger/verify_trigger_registry.py PHASE`：独立 fixture，17 项条件与注册幂等/保留关键字自检。会部署、重启游戏，必须先完成构建。
- 加 `--stress`：测试环境下启动期注册 256 个 alias，验证各 alias 与 2000 个组合判断。结束后恢复基本 fixture 再正常启动。
- `modules/trigger/test_trigger_registry_native.py OUTPUT`：注册器真实源码与受控引擎替身，22 项 API 检查。
- `modules/trigger/probe_trigger_tooltip.py`：只在已就绪游戏中使用，捕获真实本地化上下文并同步验证 tooltip 文本；不证明 UI 目视布局。

实现与限制见 `ai_docs/10_Trigger系统/注册器API与验证.md`。

## 数值系统测试入口

scalar64、typed Trigger、Array64正式接口/历史检查点及原生夹具统一见[numeric_system.md](numeric_system.md)。
最新a64soak配对已推进状态；旧检查点驱动不能直接套当前游戏。137/137是功能断言，资源增长仍待归因。
本轮只整理文档，不重跑游戏测试。

## 用户侧待办与验收取舍

[用户尚未测试的待办事项](用户尚未测试的待办事项.md)仅列真实画面/手动体验和真人环境协调。
用户接受当前资源增量，超过2GB增长才算严重问题（不是总进程内存2GB）；不要求解决掉电。自动资源监测不转移为用户专属待办。

## 外部调试控制台

2026-10-13第一版已实现，使用、自动测试与边界见[外部控制台测试入口](external_console.md)。`-debug`自动打开，可用`-no-plugin-console`禁止自动弹出；用户显示体验单独列在[用户待办](用户尚未测试的待办事项.md)的U04。

最新外部控制台保护与45分钟共享运行核结果见[抗压记录](console_stress.md)，实际GUI/GPU与多人边界不扩大为通过。
