# 遗留实现清理与Effect注册表

2026-10-14，源码规范化第六批。删除没有有效生产入口的旧实现，并将7个scalar64 Effect的注册映射集中到一张表。
不改变现有Effect名称、scope、factory标记、原版回退或hook安装策略。

## 删除前如何确认没有入口

在全部已跟踪src的C/C++/header/inc中核对token引用，并检查static链接、Effect/command表与hook安装代码。
排除待删除函数集合自身后，10个函数均没有剩余生产引用。
相关状态和地址常量在排除该集合后只有自身声明，没有其他用途。
这证明本工程当前生产路径没有接线，不承诺任意外部调试工具仍能找到旧私有符号。

## 删除的闭包

| 类别 | 删除项 |
|---|---|
| 未安装的旧原版detour | `Var64_RoundDetourUnused`、`Var64_ModuloDetourUnused` |
| 旧语法/作用域实验 | `Var64_MakeGameVarInstance`、`ExecVar64Diag`、`ExecVar64SetA/AddA/ShowA`、`Var64_ReadParamRaw`、`Var64_LogOp` |
| 未再调用的名字表查询 | `Var64_IsSixtyFourBitName` |

同时移除仅供这些实现使用的2个原函数指针、5个地址/布局常量与1个操作计数器。
名字登记/注销表仍用于现有日志去重，没有因查询函数未使用就一起删除。
公开slot getter/setter/add/name Interface、loadgame命令和真实的marked64处理函数保留。

## 不是删除round/modulo功能

`round_variable64`、`modulo_variable64`仍通过各自factory标记和 `Var64_GameSyntaxDetour`进入 `Var64_DoRoundVariable64` / `Var64_DoModuloVariable64`。
被删除的是原来就没有安装的旧原版round/modulo detour。
`Var64_InstallArithmeticHooks`函数体逐字相同，仍安装add/sub/mul/div/clamp/clear路径，不新增round/modulo hook。
原日志的“round/modulo disabled”仍指这两个原版hook，不是64位Effect被禁用。

## 一张注册映射表

`Var64EffectBinding`将每个EffectDef、fill函数、marked factory放在同一行，避免维护四处相关列表。
顺序仍是set、add、log、modulo、round、clamp、clamp_high。
注册步骤保持：所有fill先执行，再绑定所有factory、同步批量注册、仅OK状态更新entryVt[0]、安装syntax/arithmetic hooks、记录结果。
没有把“先完成全部fill”改成注册时逐项插入；没有对失败项或缺image新增恢复策略。
临时definitions数组只供同步 `Effect_RegistryRegisterAll`使用；该函数不保留数组，EffectDef对象仍为原静态对象。
entryVt slot按原成功条件逐项读取/更新，不提前无条件读取，也不改写其他slot。

## 验证与文档延续

27268组注册输入对照真实EFF_DEF声明、同步批量注册函数与RegisterEffects，覆盖ready/image、7项全部三态组合、既有state、factory映射、token和entryVT、支持scope回调及安装调用顺序。
三态stdout逐字节相同、stderr为空、exit0；factory顺序等还由夹具固定期望验证。
十套连带回归通过，原56个保留static定义不变，其他87个原有src文件哈希不变。
主文件1677行降至1317行，本轮是真正删除无入口代码并合并重复注册逻辑，不仅是移到其他文件。
历史文档保留旧函数和失败实验，但已标明源码清理后不再作为当前操作入口。
复现：[遗留清理与注册回归](../../test/docs/var64_cleanup.md)。
