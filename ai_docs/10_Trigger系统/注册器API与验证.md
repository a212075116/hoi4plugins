# Trigger 注册器 API 与验证

> 2026-10-12；HOI4 1.19.3 / Windows x64。首版提供 **bool 标量 trigger**，不是数值或块参数注册器。
> callback 的 scope 是 trigger 求值链传入的 opaque 上下文，不能直接当成 Effect scope 或本地化上下文使用。
> 首版 Bool 证据保留如下；后续数值/比较块与类型化 adapter 见 [数值块模板与Scope适配](数值块模板与Scope适配.md)，多人顾虑见 [协调测试说明](多人环境顾虑与协调测试.md)。

## 已实现

独立模块 `src/plugin/SDK_RVA/trigger/`，接入 plugin.vcxproj 和插件初始化流程。
与 Effect 共用原版 token 管理器，但注册表、entry、工厂、实例虚表和求值入口完全分开。

| 接口 | 用途 |
|---|---|
| Trigger_RegistryReady | lexer 同步初始化、trigger 对象与 map head 可读 |
| Trigger_RegistryRegister | 注册单个定义；重复注册同一对象幂等 |
| Trigger_RegistryRegisterAll | 注册定义数组，返回成功数量 |
| Trigger_RegistryRegisteredCount | 本模块成功注册数量，不是游戏所有 trigger 数量 |
| TRG_BOOL_DEF | 声明定义、工厂、求值与 tooltip 适配器 |
| Trigger_ParamBool | 读取实例中的 yes/no 参数 |
| Trigger_EvaluateBool | 比较 predicate 实际值与脚本要求的 yes/no |
| Trigger_NewInstance | 用原版 CAlwaysTrigger 工厂创建实例并替换虚表 |
| Trigger_BuildTooltip | 原版本地化格式化与 yes/no 目标文本 |

## 增加一个 trigger

```c
#include "trigger_reg.h"

static int __fastcall HasScope(void* self, void* scope)
{
    (void)self;
    return scope != NULL;
}

TRG_BOOL_DEF(has_scope, "my_has_scope", "Checks a scope pointer.", "MY_HAS_SCOPE", HasScope)

int RegisterMyTriggers(void)
{
    TriggerDef* defs[] = { &has_scope_def };
    has_scope_fill();
    return Trigger_RegistryRegisterAll(defs, 1);
}
```

调用注册必须在脚本解析之前。定义、name/desc/locKey、虚表和 callback 必须维持整个进程生命周期。
不支持运行中注销、卸载插件或任意线程并发注册。predicate 应保持只读、无文件 I/O 和游戏状态修改。
名字为 1..63 字节小写 ASCII 字母、数字、下划线，首字符不能是数字。

```text
my_has_scope = yes
NOT = { my_has_scope = yes }
OR = { my_has_scope = no always = yes }
```

predicate 返回非零表示实际条件为真；`= no` 由适配器自动反向匹配。
AND/OR/NOT 和条件组合继续由游戏处理。数值、变量名、`{ var=... value=... }` 不属于本版参数形态。

## 原生依据

| 项目 | RVA / 布局 |
|---|---|
| trigger 注册对象槽 | 0x3330050；std::map 位于对象 +24 |
| 注册函数 | 0x550970，参数 object/id/entry |
| CAlwaysTrigger 工厂 | 0x3E32B0，原版分配 0x60 字节 |
| 实例虚表 | 0x278A3A0，23 槽 |
| bool 参数 | 实例 +88 |
| 原版实际求值 | 虚表 +0xB0 / 槽 22，原函数 0x3CFD80 |
| 外层 scope 校验 / 求值包装 | 虚表 +0x18，原函数 0x54D0B0，调用 +0xB0(self, scope) |
| tooltip | 虚表 +0xA8 / 槽 21，原函数 0x3F2080 |
| CTriggerEntry<CAlwaysTrigger> 虚表 | 0x27A14D8；工厂在 +8 |
| entry 对象 | 24 字节；描述 +8；标志 +16=1，不是 Effect 的 16 字节对象 |
| 原版分配/释放 | 0x21C9AF0 / 0x21C9B00 |

entry 由游戏 CRT 分配并交给注册表持有；实例也由原版工厂分配。
两套复制虚表均保留原版 COL/RTTI 前缀和原版析构器，避免交给游戏释放插件 CRT 或静态内存。
不能把 Effect 的 +0x68 执行槽或参数读取器用在这个 96 字节 trigger 上。

## 两个关键修正

1. **不能只检查 trigger map 来防原版关键字冲突。** 初始化早期 `always` 可能尚未入表。
   使用原版 token API取得规范 id，再按静态 token 表的整数 id 拒绝保留关键字；同时拒绝已有 trigger entry。
   同一 token API 对已存在名字返回原 id，不另造别名。
2. **token 记录不是 MSVC std::string @+8。** 运行期 always 记录与旧假设不同。
   不再读取未证实的名字布局；仅使用原版 token API 和已确认的 72 字节记录 +0 id。

注册状态为 PENDING/OK/FAILED；not-ready 保持待注册；分配失败可以在修正条件后重试。
正常定义重复调用不增加数量；不同对象占用同名和所有原版静态关键字均拒绝。

## 本轮结果与证据链

| 验证 | 结果 |
|---|---|
| 没有注册器的基线 | 10/17，42 条本 fixture 解析错误；说明正分支偶然正确不等于 trigger 存在 |
| 注册器基础条件 | 17/17；yes/no、真/假、AND/OR/NOT、嵌套和另一国家 scope |
| 原生 API 夹具 | 22/22，含幂等、重复名、原版尚未入表、非法名字、分配失败/重试 |
| 实际游戏格式化路径 | 三个自定义 tooltip 均得到本地化文本与 `= yes` |

tooltip 测试在 log 的真实 CContextLocalizationText 回调生命周期内同步调用，不把 trigger scope 当作本地化 ctx。
这是原生格式化文本的验证，不是鼠标悬停、UI 颜色或布局的目视验收。
原生 API 夹具使用实际注册器源码，token/map/allocator 是受控替身；实际 ABI 由游戏测试另行验证。

Evidence：`test/reports/20261012_variable64_transaction/trigger/` 的静态记录、原生结果、各轮日志和 comparison.json。
Finding：基础注册、参数解析、求值和原版隔离已打通；初始化时序与 token 布局两项问题已修正。
Path：先完成 17/22/3 项基本验证，再启用仅用于测试的批量注册模式与重复求值。

## 后续抗压与边界

测试模式需显式设置进程环境变量 `HOI4_TRIGGER_REG_STRESS=1`，默认只注册 3 个示例。
该模式启动期额外注册 256 个 alias，总数 259；随后验证全部 alias 的 yes/no，以及 1000 次真组合和 1000 次假组合。
期望：bulk_yes=256、bulk_no=0、repeat_yes=1000、repeat_no=0。本轮实际一致，fixture 错误为 0。
离开测试模式前重新写回基本事件文件，以免下一次普通启动解析未注册的 bulk 名字。
本轮已恢复正常模式，仅注册 3 个示例；随后 variable64 516/516 与原有 48/48 再跑通过，污染为 0。

首轮未覆盖：数值/块参数模板、variable64 比较、trigger scope 的类型化适配器、热注册/卸载、多线程、长期运行和完整 UI 目视。
后续已完成数值/比较块与 scope adapter 的所列单人验证，当前正常模式注册 5 个示例（3 Bool +2 typed）。
实现与剩余边界以 `数值块模板与Scope适配.md` 为准，不能把首轮 3 个示例的历史结果当作当前模块全部状态。
