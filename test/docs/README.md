# 测试脚本总览（test/）

> 本目录是**探针与测试脚本**。改插件前先看这里，不要凭记忆写新脚本。
> 测试报告放 `test/reports/`，技术结论写 `ai_docs/`。

## 目录结构

| 目录 | 用途 |
|---|---|
| `docs/` | **本目录**，说明每个脚本怎么用、能干啥 |
| `lib/` | **公共库，不要移动**（见下表） |
| `modules/<模块名>/` | 按模块归类的探针与运行脚本，**活跃脚本都在这里** |
| `archive/` | 历史一次性探针（探索期产物，不再维护） |
| `reports/` | 测试报告、截图、CE 表 |

## 公共库（`lib/`）

| 文件 | 作用 |
|---|---|
| `frida_host.py` | Frida 宿主：`find_pid` / `connect` / `wait_in_game` / `detach` |
| `exec_console_command.js` | **最常用的探针**：进程内执行控制台命令 `exec(命令, 参数[])` |
| `idalib_cli.py` | 向 idalib 常驻服务发查询（decompile / disasm / xrefs_to / strings / names / vtable） |
| `idalib_server.py` | idalib 常驻服务本体（TCP 127.0.0.1:19531） |
| `probe_common.py` | 探针公共小工具 |

**`lib/` 里的路径是写死的，所有脚本都引用它 —— 移动它会连带 200+ 个脚本失效。**

## 模块目录

| 模块 | 对应源码 |
|---|---|
| `modules/gamedate/` | `SDK_RVA/gamedate/`（日期读写、界面刷新） |
| `modules/camera/` | `SDK_RVA/camera/`（摄像机高度） |
| `modules/console/` | `SDK_RVA/console/`（控制台指令注册） |
| `modules/effect/` | `SDK_RVA/effect/`（Effect 注册与执行） |
| `modules/hook/` | `SDK_RVA/hook/`（文件重定向、进程拦截、inline hook） |
| `modules/crash_test/` | `SDK_RVA/crash_test/`（崩溃测试命令） |

## 怎么跑一个脚本

```
# 1) 游戏必须先用 Start-Process 独立启动（绝不能 frida.spawn）
Start-Process -FilePath '<游戏根>/hoi4.exe' `
  -ArgumentList '-gdpr-compliant -start_tag=ABY -nolauncher' `
  -WorkingDirectory '<游戏根>'

# 2) 等它进图（约 40~60 秒），然后跑脚本
python -u test/modules/<模块>/<脚本>.py [参数]
```

## ⚠️ 三条硬规则（都踩过，代价很大）

**1. 不要用 `frida.spawn`**

spawn 出来的游戏进程会随宿主 Python 进程结束被一起终止，现象是「一跑完脚本游戏就没了」，
**会被误判成崩溃**。标准做法：外部 `Start-Process` 启动，脚本里 `connect(force_spawn=False)`。

**2. 不要在同一进程里反复 connect/detach**

快速反复开关 Frida 会话会把游戏搞死，现象同样是无 dump、无事件日志。
**一个脚本只 connect 一次**，把所有操作做完，最后 detach 一次。
需要同时用多个探针时，在那个 JS 探针里多写几个 rpc 方法，而不是开两个会话。

**3. `auto_unpause` 是开关，不是「取消暂停」**

每调一次在开/关之间切换，**必须看返回值确认状态**。
调试时被这条坑过：以为游戏在跑，其实是自己把它切回暂停了。

## 其它容易忘的点

- 游戏进图后**默认暂停**，日期不推进；要 `auto_unpause <1..5>` 才会走
- **游戏刚进图的头 ~25 秒内写入会被它自己重置**，要等稳定
- `CGameState`（`*(hoi4.exe+0x332F260)`）非 NULL ≠ 已进图，主菜单也可能非 NULL；
  判据是 `game.log` 里的 `[[ Launching SINGLEPLAYER-game ]]`
- 编译前**先杀游戏**，否则 `LNK1201`（pdb 被占用）
- 部署要**同时覆盖 `tbb.dll` 和 `hoi4_mod_plugin.dll`**，且杀游戏后等几秒再复制

## 历史目录（探索期产物，不再维护）

下面这些是早期探索留下的**一次性探针**，约 700 个，名字多为 `_arm.js` `_cam2.js` 这类
只能靠记忆的名字。**它们没有被移动**（脚本间路径引用太多，移动风险大于收益）。

| 目录 | 内容 |
|---|---|
| `probes_js/` | 早期 JS 探针（活跃的已移入 `modules/`） |
| `probes_frida/` | 早期 Python 宿主脚本 |
| `tools/` | 早期运行脚本与工具（公共库已移入 `lib/`） |
| `probes_ida/` `probes_idalib/` `probes_py/` | 早期 IDA 批处理与纯 Python 脚本 |
| `jobs/` | 早期后台任务产物 |

**要用某个历史脚本时**：先在 `reports/` 或 `ai_docs/` 里搜它对应的结论，
再决定是否值得翻出来；**不要直接照着它的名字猜用途**。

新增脚本一律放 `modules/<模块>/`，不要再往历史目录里加。

## 命名约定

| 形式 | 含义 |
|---|---|
| `modules/<模块>/<动词><名词>.js` | 探针，用 `rpc.exports` 暴露能力 |
| `modules/<模块>/<动词><名词>.py` | 运行脚本，加载探针并驱动它 |
| `lib/*` | 公共库 |

名字要能望文生义，例如 `read_game_date_fields.py`、`set_game_date_with_argument.py`。
不要再出现 `_a2.js`、`_chk3.py` 这类只能靠记忆的名字。
