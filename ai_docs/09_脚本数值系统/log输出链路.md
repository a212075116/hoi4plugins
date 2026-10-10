# 原版 log effect 与 game.log 输出链路（静态查证）

> 来源：idalib 对 `sources/1.19.3/hoi4.exe.i64` 的静态分析（IDA 基址 `0x140000000`）；
> 本轮未做动态验证，凡未验证处均标 ⚠️。
> 目的：为「让 log 输出 variable64 的完整 64 位值」提供依据，并核对工作区未提交代码的正确性。

## 一、log effect 的注册（已查证）

| 项 | 值 | 来源 |
|---|---|---|
| effect 名 | `log` | 描述串 @ `0x1429B64C0`（RVA `0x29B64C0`） |
| **effect id** | **10676**（`0x29B4`） | `sub_140079740` 里 `mov edx, 29B4h` |
| 注册函数 | `sub_140079740`（92 字节，RVA `0x79A0` 附近） | xref → `0x1429B64C0` |
| entry 虚表 | `CEffectEntry<CLogScriptEffect>::vftable` @ `0x1429B7588`（RVA `0x29B7588`） | 反编译 `sub_140079740` |
| entry 工厂（槽 +8） | `0x1413930B0`（RVA `0x13930B0`） | 读虚表 |
| 实例类 | `CLogScriptEffect`（RTTI `0x143262130`） | `names` |
| 实例虚表 | `0x1429B73D8`（RVA `0x29B73D8`） | `names` |
| **exec（槽 +0x68）** | **`0x141393DF0`（RVA `0x1393DF0`）** | 读虚表 |
| 描述原文 | `Print message to game.log, console (if visible) and history logger (if running. you can use category|log to specify a category), Can be localized` | `0x1429B64C0` |

同 id 另有一个 trigger 版：`CTriggerEntry<CLogScriptTrigger>`（`sub_140079B30`，96 字节，
描述串 `0x1429B80F0`）。**这就是「log 既能当 effect 又能当 trigger」的原因。**

## 二、exec 的完整调用序列（`sub_141393DF0` 反编译，1272 字节）

入参：`a1` = 实例，`a2` = scope。实例布局：`+88` 是 std::string（日志文本），cap 在 `+112`。

```c
text = (实例 + 88) 的 std::string          /* cap>15 时 data 在 *(实例+88) */
sub_142245E60(&v32, text, 0, 0);            /* RVA 0x2245E60 —— 项目里的 RVA_EFF_PACKKEY */
sub_1410E48A0(&v30, a2, &v32);              /* ★ RVA 0x10E48A0 —— 文本替换（本地化 + [?变量]） */
sub_142245E60(&v26, /*v30 的数据*/, 0, 0);  /* 替换后的文本 */

logger = sub_1424C9240();                   /* RVA 0x24C9240 —— CLogger 单例 */
sub_1424C9AE0(logger, v34,                  /* RVA 0x24C9AE0 —— CLogStream 构造 */
              "C:\\mnt\\gsg\\hoi4\\hoi4_merged\\hoi4\\source\\effects\\effectbase.cpp",
              1783, 65539);
sub_1424C8D60(v34, &v26);                   /* RVA 0x24C8D60 —— 往流里写文本 */
sub_14011D290(/*stream*/, "\n");             /* RVA 0x11D290 —— 追加换行 */
sub_1424C89E0(v34 + 160);                   /* RVA 0x24C89E0 —— CLogStream 析构（真正输出） */
v35[0] = &std::ios_base::vftable;
sub_14251C47C(v34 + 160);                   /* RVA 0x251C47C —— std::ios_base 析构 */
```

**行号 1783 与游戏日志里的 `[effectbase.cpp:1783]` 完全对上**，证明该函数就是 `log = "..."` 的执行体。
另有 `1799` 分支（`byte_14332EC69` 为真时再写一行，走 `sub_140129FD0`）。
`65539` = `0x10003`，是日志 flags。

栈布局可推出 **CLogStream 对象大小 = 256 字节**（`v34[160]` 紧跟 `v35[12*8]=96`），
与构造函数最远写 `+248` 吻合。

## 三、输出链函数总表（全部已查证）

| IDA 地址 | RVA | 作用 | 依据 |
|---|---|---|---|
| `sub_1424C9240` | `0x24C9240` | **CLogger 单例 getter**（首次调用 malloc 0x48 并构造 `CLogger`/`CNullLogger`） | 反编译 |
| `sub_1424C9AE0` | `0x24C9AE0` | **CLogStream 构造函数**（`a1`=logger，`a2`=对象，`a3`=文件，`a4`=行号，`a5`=flags） | 反编译 |
| `sub_1424C8D60` | `0x24C8D60` | 把 std::string 写进流（返回流自身） | 反编译 |
| `sub_14011D290` | `0x11D290` | 写字符串/换行（681 字节，`operator<<` 系列） | 调用点 |
| `sub_1424C89E0` | `0x24C89E0` | **CLogStream 析构**：取缓冲内容 → 调 `logger->vft[+8]` 真正输出 | 反编译 |
| `sub_14251C47C` | `0x251C47C` | `std::ios_base` 析构（`_Tidy`） | 反编译 |
| `sub_142245E60` | `0x2245E60` | std::string 拷贝助手（项目已有 `RVA_EFF_PACKKEY`） | 已用 |
| `sub_1410E48A0` | `0x10E48A0` | 文本替换封装：建上下文 + 调替换器 | 反编译 |
| `sub_1412CED60` | `0x12CED60` | **真正的替换器**（1347 字节，30 处引用） | func + 调用点 |
| `sub_1410E2160` | `0x10E2160` | 替换上下文构造（1271 字节） | 反编译 |

### 3.1 真正的输出点

`sub_1424C89E0` 内部：

```c
v3 = *(a1 - 32);                                   /* logger 指针 */
v4 = *(void**)(*(_QWORD*)v3 + 8);                  /* logger 虚表 +8 槽 */
v4(logger, *(a1 - 12) /*line*/, &fileStr, flags, &textStr);
```

即 **输出动作在 `CLogger` 的虚表 +8 槽**。
`CLogger` 基类虚表 `0x142B91D18`（4 槽）里的 +8 是 `_purecall`，
实际实例是派生类：`CFileLogger`（vftable `0x142B3AC78`）/ `CFilterLogger`（`0x142B3AF58`）。

## 四、对工作区未提交代码的核对（★ 重要）

`src/plugin/SDK_RVA/variable64/variable64.c` 工作区版本（**未提交**）新增了：

```c
#define RVA_LOG_GET        0x24C9240u
#define RVA_LOG_OUT        0x24C9AE0u
#define VAR64_LOG_FLAGS    0x10003LL

((Var64LogOutFn)(img + RVA_LOG_OUT))(logger, message, kVar64LogFile, 1LL, VAR64_LOG_FLAGS);
/* Var64LogOutFn = void (logger, const char* text, const char* file, long long line, long long flags) */
```

查证结论：

| 判断 | 依据 |
|---|---|
| `RVA_LOG_GET 0x24C9240` = CLogger 单例 getter —— **用法正确** | `sub_1424C9240` 反编译 |
| `RVA_LOG_OUT 0x24C9AE0` **不是输出函数**，是 **CLogStream 构造函数** | `sub_1424C9AE0` 反编译 |
| 现用法把 `char msg[128]` 当 CLogStream 对象传入，构造函数会写到 `msg+248` | **栈越界写 ≥120 字节** |
| 该调用**没有任何测试报告与文档依据** | `test/reports/`、`ai_docs/` 均无记录 |

⚠️ **该代码按现状会破坏栈，属于未验证且用法错误的改动。**

正确的最小序列（⚠️ 伪造，尚未动态验证）：

```c
unsigned char stream[0x100];                       /* CLogStream = 256 字节，必须可写 */
logger = ((CLoggerGetFn)(img + 0x24C9240))();
((LogStreamCtorFn)(img + 0x24C9AE0))(logger, stream,
        "...\\effectbase.cpp", 1783, 0x10003LL);
((LogStreamWriteFn)(img + 0x24C8D60))(stream, &textStdString);   /* 需 std::string，不是 const char* */
((LogStreamWriteFn)(img + 0x11D290))(stream, "\n");
((LogStreamDtorFn)(img + 0x24C89E0))(stream + 0xA0);
((IosBaseDtorFn)(img + 0x251C47C))(stream + 0xA0);
```

## 五、[?变量] 替换的 hook 点（需求「log 输出 64 位」的关键）

`[?名字]` 的展开发生在 `sub_1410E48A0` → `sub_1412CED60` 这一层。

| 方案 | 做法 | 影响面（引用数已实测） |
|---|---|---|
| A | hook `sub_1412CED60`（RVA `0x12CED60`），替换后扫描文本，把我们的 64 位值塞进去 | **30 处引用**，实际改写文本的地方 |
| B | hook `sub_1410E48A0`（RVA `0x10E48A0`） | **1055 处引用** —— 它是**通用文本替换 API**，不止 log 用 |
| C | 不动原版，我们的 effect 用第四节那条序列**自己写 game.log** | 只在我们的 effect 内生效；`[?var]` 仍只显示 32 位 |

`sub_1424C9240`（CLogger getter）有 **12158 处引用** —— 游戏所有日志都从这里取 logger，
说明「自己写 game.log」这条路用的是游戏的正式日志通道，不是旁路。

## 六、待验证清单

| 项 | 说明 |
|---|---|
| CLogStream 的精确栈布局 | `stream+0xA0` 是否为析构入参，需动态验证 |
| `sub_1424C8D60` 第二参数 | 从反编译看是 **std::string***（读 `+24` 判 SSO），不是 `const char*` |
| 日志刷盘时机 | 析构即在 `sub_1424C89E0` 内完成，还是有额外 flush |
| 动态写入验证 | 需在游戏内跑一次，确认 game.log 出现我们写的行 |

## 七、相关文档

| 主题 | 文档 |
|---|---|
| log 与本地化格式化语法 | `log与变量格式化.md` |
| variable64 实现与验证历程 | `variable64实现与验证.md` |
| variable64 的 effect 实现 | `variable64的effect实现.md` |
| 变量与定点数 | `变量与定点数.md` |
