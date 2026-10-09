# 日期 Effect 与指令

> 本页只讲**插件对外提供的接口**；日期的内存布局、编码与验证见《游戏日期.md》。
> 原始测试记录：test/reports/20261010_0355_插件_gamedate_日期effect与指令_验证.txt
## 本项目提供的接口（已实现并验证）

### 控制台指令

| 指令 | 作用 |
|---|---|
| `setgamedate <年.月.日.小时>` | 设为指定日期；无参数时回显当前日期 |

别名 `sgd`。实测：`setgamedate 510.6.7.0` → 回显 `510.6.7`，`game.log` 前缀变成 `0510.06.xx`。

### effect

| effect | 作用 |
|---|---|
| `set_game_date = 510.6.7.0` | 设为指定日期（本地化 key `EFFECT_SET_GAME_DATE`） |

实测（插件日志）：

    [eff] set_game_date #1  arg=[510.6.7.0]   raw 48180000 -> 48271368
    [eff] set_game_date #2  arg=[515.3.20.0]  raw 48271368 -> 48313272
    [eff] set_game_date #3  arg=[500.1.1.0]   raw 48313272 -> 48180000

### 源码

| 文件 | 作用 |
|---|---|
| `SDK_RVA/gamedate/gamedate.h` | 接口与偏移常量 |
| `SDK_RVA/gamedate/gamedate.c` | 读写日期、文本解析、指令注册 |
| `SDK_RVA/effect/effect_gamedate.c` | effect 注册与执行 |

注册在 `plugin_main.c`：effect 在 `EffectCameras_Register()` 之后，
指令在 `Camera_RegisterCommands()` 之后。

### 两个实现细节（都踩过）

**1. 参数从 effect 实例 `+0x108` 读**（MSVC `std::string`：数据 / 长度 / 容量），
要同时处理 SSO（容量 <= 15）与堆指针两种情形。

**2. 没有用游戏自己的解析函数 `sub_140533D60`。**
它签名是 `(CGameDate*, std::string*)`，看着最合适，但**实测恒返回 0 且不写值**
（它的前置检查 `sub_14029D420(buf, "%d.%d.%d.%d") <= 2` 中，IDA 未显示该函数的输出参数，
实测传正确字符串仍失败）。所以改为自行解析 + 用实测公式计算。

### 派生字段是 0-based

回显时要加 1：

    +0x488 = 月 - 1        +0x480 = 日 - 1        +0x484 = 年内第几天(0-based)

即 `500.1.1` 对应 `+0x488=0` `+0x480=0`。**早期把它当成 1-based，导致回显差 1 天。**

### 事件测试的正确写法

要触发 effect 需要事件。HOI4 事件文件必须是：

    add_namespace = zzdatetest          // 不是 namespace =

    country_event = {                   // 必须有这层包裹
        id = zzdatetest.1
        hidden = yes
        is_triggered_only = yes
        immediate = { set_game_date = 510.6.7.0 }
        option = { name = zzdatetest.1.a }
    }

只写 `zzdatetest.1 = { ... }` 会报 `Unexpected token`（error.log 里能看到）。

### 部署提醒

改插件后必须覆盖**两个**产物（`tbb.dll` 与 `hoi4_mod_plugin.dll`），
且**先杀掉游戏并等几秒**，否则 `Copy-Item` 会因文件被占用而静默失败，跑的还是旧插件。
## 日期加减（已实现并验证）

### 控制台指令

| 指令 | 别名 | 作用 |
|---|---|---|
| `addtimeforyears <n>` | `atfy` | 加 n 年（n 可为负） |
| `addtimeformonths <n>` | `atfm` | 加 n 月 |
| `addtimefordays <n>` | `atfd` | 加 n 天 |
| `addtimeforhours <n>` | `atfh` | 加 n 小时 |

无参数时回显当前日期（含小时）。

### effect

| effect | 作用 |
|---|---|
| `add_time_for_years = n` | 加 n 年 |
| `add_time_for_months = n` | 加 n 月 |
| `add_time_for_days = n` | 加 n 天 |
| `add_time_for_hours = n` | 加 n 小时 |

### 实现方式与数学

因为**每年固定 365 天、无闰年**，所以：

| 单位 | 做法 |
|---|---|
| 小时 | `raw += n` |
| 日 | `raw += n * 24` |
| 年 | `raw += n * 365 * 24` |
| **月** | **必须做日历运算**：解出年月日，月 `+= n`，进位/借位到年，再把日 clamp 到该月天数（如 1月31日 +1月 → 2月28日） |

小时/日/年只改 raw，**不碰年月日**，因此不存在月末越界问题。

年月日的解算用 `GameDate_DecodeRaw`（纯计算，**不读派生字段**），
与写入用的 `GameDate_EncodeParts` 互为逆运算。

### 实测（基准 510.6.7，速度 2）

    加 10 年  -> 520.6.7       加 3 月   -> 520.9.7
    加 45 天  -> 520.10.22     加 100 时 -> 520.10.26.4
    减 30 天  -> 520.9.26.4    减 5 月   -> 520.4.26.4
    减 3 年   -> 517.4.26.4    减 50 时  -> 517.4.24.2

八个用例（指令与 effect 各跑一遍）结果一致，负数正常。

验算：9月7日 +45天 → 9月剩 23 天，再 22 天进 10 月 = 10月22日；
10月22日 +100小时 → +4天4小时 = 10月26日4时。

### 关于年份显示的一次错误

`GameDate_DecodeRaw` 起初写成 `year = days/365 + 500`，
但 `days`（即 `raw` 减基准后除 24）**已经是绝对天数**（`182500 + 相对天数 = 365×年 + ...`），
再加 500 就变成了 `1010`（并导致后续每次加减都多 500）。去掉即可。

### 写入时机（重要）

**游戏刚进图、还在初始化时写入会被它自己重置回去。**
实测：进图后头 10 秒内 `add_time_for_years 10` 写成功（日志里 raw 已变），
但下一次读回变成 `2.1.1`；等游戏稳定后（并 `auto_unpause`）再写就正常保持。
所以脚本里要等 `game.log` 出现进图标记，并再等若干秒。
