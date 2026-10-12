# Effect 注册器 API

> 文件：`SDK_RVA/effect/effect_reg.h`（接口）、`effect_reg.c`（实现）
> 一个具体 effect 的示例见 `SDK_RVA/effect/effect_camera.c`。

## 为什么需要注册器

注册一个 effect 要处理两件麻烦事：

1. **工厂**（`entry` 虚表 `+0x08`）是**无参调用**，函数里不知道自己属于哪个 effect
2. **工具提示**（实例虚表 `+0x38`）需要各自的本地化 key

解决方式：**每个 effect 有自己的虚表 + 自己的那两个函数**，
用宏 `EFF_DEF` 在编译期把它们和 `EffectDef` 绑定。

## 加一个 effect：三步

### 1. 写执行函数

    static void __fastcall ExecMyThing(void* self, void* scope)
    {
        float v = Effect_ParamFloat(self, scope);   // 取脚本里给的值
        MyApply(v);
    }

签名固定为 `void __fastcall(void* self, void* scope)`。

### 2. 用宏声明

    EFF_DEF(mything, "my_thing", "Does my thing", "EFFECT_MY_THING", &ExecMyThing)

| 参数 | 含义 |
|---|---|
| `mything` | 标识符前缀，宏会生成 `mything_def` / `mything_factory` / `mything_tooltip` / `mything_fill` |
| `"my_thing"` | **脚本里用的名字**（不能空、不能以数字或 `-` 开头） |
| `"Does my thing"` | 内部描述（`entry+8`，游戏内部用） |
| `"EFFECT_MY_THING"` | **本地化 key** |
| `&ExecMyThing` | 执行函数 |

### 3. 加进清单并注册

    static EffectDef* g_effects[] = { &mything_def };

    void EffectXxx_Register(void)
    {
        mything_fill();                                     // 必须先 fill
        Effect_RegistryRegisterAll(g_effects, 1);
    }

## 本地化

`localisation/<lang>/xxx.yml`，**UTF-8 带 BOM**：

    l_simp_chinese:
     EFFECT_MY_THING: "我的效果：$VAL$。"

`$VAL$` 会被替换成定点值（脚本给的值 x100000，显示为两位小数）。
原版还会用 `$VAL|+=%$`（按百分比、带正负号）。

## 时序要求

注册必须在 **lexer 就绪之后、脚本解析之前**。实测：

| 事件 | 时间 |
|---|---|
| 插件线程启动 | 0 |
| lexer 就绪 | 约 2.2 秒（10ms 轮询第 ~200 次） |
| **脚本解析** | 约 14 秒 |

所以注册循环放在插件线程最前面，用 `Effect_RegistryReady()` 轮询。

    for (round = 0; round < 3000 && !ok; ++round) {
        if (Effect_RegistryReady()) ok = (EffectCameras_Register() > 0);
        if (!ok) Sleep(10);
    }

## 接口一览

| 函数 | 作用 |
|---|---|
| `Effect_RegistryReady()` | lexer 是否就绪 |
| `Effect_RegistryRegister(def)` | 注册一个；成功后 `def->tokenId` 有效、`state = EFF_STATE_OK` |
| `Effect_RegistryRegisterAll(defs, n)` | 批量注册，返回成功数 |
| `Effect_RegistryRegisteredCount()` | 已注册总数 |
| `Effect_NewInstance(vt)` | 造实例（调游戏工厂再换虚表），供生成的工厂调用 |
| `Effect_BuildTooltip(s,o,c,key)` | 生成工具提示文本，供生成的 tooltip 调用 |
| `Effect_ParamFloat(self, ctx)` | 取本 effect 的参数值（float） |

`EffectDef` 里由注册器自动填写的字段：`tokenId`、`state`、`vt[]`、`entryVt[]`、`entry[]`。
使用者只需在 `fill` 里填 `name`/`desc`/`locKey`/`exec`（宏已代劳）。

## Scope 合约（2026-10-12 已实测）

`EffectDef.supportedScopes` 为可选的 `EffectScopeFn`。NULL 保留模板限制；
需要全局操作时，在 fill 后、注册前设置 `mything_def.supportedScopes = Effect_ScopeAny`。
注册器仅替换实例虚表第 19 槽（+0x98）的 scope mask getter，不绕过原版解析/执行检查。
`Effect_ScopeAny` 返回 0，含义是没有特定 scope 限制，并非“取 global 变量容器”。

普通定义仍继承 `CAddStabilityEffect` 的国家 mask=4。
摄像机、日期定义显式使用 Any；其目标是全局摄像机/日期，不随当前国家改变。
国家、另一国家、州、角色中 add_time_for_hours/add_camera_height 的零增量均已执行；
未把零增量测试等同于所有摄像机/日期操作的极值测试。
详见 [Scope与scoped操作数验证](Scope与scoped操作数验证.md)。

## 坑：不要在工具提示路径里做文件 I/O

在 `Effect_BuildTooltip` 里直接 `Plugin_Log`（每次 CreateFile/WriteFile/CloseHandle），
会导致**游戏在第一个事件执行后崩溃**（Frida 报 `script has been destroyed`，进程随后退出）。
移除日志即恢复。

做法：**延迟输出**。

    // 工具提示里：只拷进全局缓冲，不做任何 I/O
    if (g_hasPendingTip == 0 && osz > 0 && osz < 150) {
        ...拷到 g_pendingTip; g_pendingLoc = locKey; g_hasPendingTip = 1;
    }

    // 执行函数一开始：把上一条写日志
    Effect_FlushPendingTooltip();

代价：日志里的文本是**上一次**触发的；要看最后一次需多触发一轮。

## 实现上的关键取舍

| 事项 | 做法 | 原因 |
|---|---|---|
| 实例虚表 | 从 `CAddStabilityEffect` 整体复制 25 槽，替换 exec、tooltip，按需替换 scope getter | 未指定 scope getter 的定义保留国家限制 |
| 实例本体 | 调游戏工厂 `sub_14033C420` 造好再换虚表指针 | 布局 100% 正确，不用猜字段 |
| entry 析构 | 借用游戏 `CEffectEntry` 虚表的 `[0]` | 同上 |
| 参数 | `sub_140544C90(self+0x58, ...)` | 原版做法；`+0x108` 在工具提示阶段是空的 |
| 本地化 | `sub_142245E60` 打包 + `sub_1410E48A0` 格式化 | 自己拼 `packed` 会 access violation |
