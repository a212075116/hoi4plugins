# 变量运算 effect 的 64 位版本 (modulo / round / clamp)

> 历史阶段记录：全文的“本轮/当前/下一步”仅指当时实验，不是最新状态或可直接照抄的实施指令。现状见 [当前状态与复现](当前状态与复现.md)。旧方案、失败与旧偏移保留用于追溯，不覆盖现实现。

> 状态校正（2026-10-12）：独立 `_64` effect 与原版同名 effect 是不同入口。原版 clamp 的 min/max 已接入并在本次 8 项回归通过；round/modulo 原版同名 hook 仍停用。自定义 clamp_variable64 仍采用 value 边界参数。
> 当前结论统一见《当前状态与复现.md》；下文保留历史过程，不能作为当前待办清单。

> 状态: **已实现并实测通过。** 记录时间 2026-10-11 19:22:29
> 依据: 本文所有结论均来自插件运行日志 (test/reports/ 下的报告) 与 IDA 反编译。

## 一、落地的 effect

| effect 名 | 语义 | 语法 |
|-----------|------|------|
| modulo_variable64 | 取余 (与原版同: 先舍小数再整数取模) | `modulo_variable64 = { var = x value = 1000 }` |
| round_variable64 | 四舍五入 (与原版同: 恰好 .5 时取绝对值大的方向) | `round_variable64 = { var = x }` |
| clamp_variable64 | 低于下限时提升到下限 | `clamp_variable64 = { var = x value = <min> }` |
| clamp_variable64_max | 高于上限时压低到上限 | `clamp_variable64_max = { var = x value = <max> }` |

## 二、实测数据 (game.log 原文, zzdatetest.88 / .89)

```
M64 t0=12345678901234.56789    set_variable64 大值
M64 t1=234                     modulo_variable64 { var=m6x value=1000 }  (12345678901234 % 1000 = 234)
M64 t2=234                     round_variable64
M64 t3=-1235                   round on -1234.5 -> -1235 (取绝对值大的方向, 与原版一致)
M64 t5=1000                    clamp_variable64 { value=1000 } on 345 -> 1000
M64 t6=100                     clamp_variable64_max { value=100 } on 1000 -> 100
M64 t4=1000                    clamp_variable64_max { value=1000 } on 9999999999999.99999 -> 1000
M64 t8=-1000                   clamp_variable64 { value=-1000 } on -5000 -> -1000
M64 t9=1000                    round_variable64
```

注册日志 (tokenId 由游戏分配):

```
[eff] + modulo_variable64  tokenId=20162  loc=EFFECT_MODULO_VARIABLE64
[eff] + round_variable64   tokenId=20163  loc=EFFECT_ROUND_VARIABLE64
[eff] + clamp_variable64   tokenId=20164  loc=EFFECT_CLAMP_VARIABLE64
```

## 三、为什么 clamp 要拆成两个 effect

**原因: 自定义 effect 借用的 entryVt 只认识 `var` 与 `value` 两个参数名。**

我们注册自定义 effect 时 (`effect_reg.c`), `entryVt[0]` 取自 set_variable 的模板
(RVA `0x277C418`), 而该模板只解析 `var` / `value`。原版 clamp_variable 用的
`min`(+296) / `max`(+504) 这两个参数名根本解析不进来。

实测: `clamp_variable64 = { var = x min = 0 max = 1000 }` 会直接让 effect 报错
(`out->ok = 0`)。改为 value 传边界并拆成两个 effect 后通过。

**注意**: 写成 `{ var = x min = ... max = ... }` 时 min/max 会被**静默忽略**
(既不报错也不生效), 使用者容易误以为生效了。

## 四、已知的两个行为约束

1. **数值上限 92233720368547.75807**
   这是游戏定点 raw 的 int64 上限 (2^63-1 / 100000)。超过会回绕。
   实测用 123456789012345 时得到 -61010651724749.83725, 与 2^64 回绕吻合, 属于游戏固有行为。

2. **round_variable64 不支持简写形式**
   `round_variable64 = x` 不行, 必须写 `{ var = x }`。
   原因: 原版 round_variable 从实例 +88 直接取槽 (不走 +200 名字字段),
   而我们的解析从 +200 读名字, 简写时那里为空。

## 五、相关文件

```
实现: src/plugin/SDK_RVA/variable64/variable64.c
事件: mod/bakaifa/events/zz_numtest.txt  (zzdatetest.88 / .89)
报告: test/reports/20261011_1643_..._三运算符64位版_验证.txt
```
