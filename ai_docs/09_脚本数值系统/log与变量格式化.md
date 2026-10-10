# log 与本地化里的变量格式化

> 来源：用户下载的 `wiki/Localisation - Hearts of Iron 4 Wiki.html`（4.2 Formatting variables）
> 以及实测 `test/reports/20261010_2125_原版_set_variable数值上限与溢出_实测.txt`

## 语法

    [?变量名|修饰符]

变量名可用点号接作用域或函数，例如 `[?global.date.GetDateString]`、`[?GER.var_name]`。

## 修饰符（仅变量可用）

| 修饰符 | 作用 | 例子 |
|---|---|---|
| 颜色字母 `R` / `G` / `Y` 等 | 改文字颜色 | `[?my_variable|R]` 变红 |
| `SI` | **除以 1000/1000000 并加 K 或 M 后缀**，默认 2 位小数 | `65536` -> `65.53K`；`1500000` -> `1.50M` |
| 数字 `0` ~ `5` | **小数位数，最多 5 位**，超过按 5 处理 | `[?var|2]` |
| `%` | 乘 100 并加百分号，默认 2 位小数 | `[?var|%]` |
| `+` | 显示正负号，正数绿、负数红 | `[?var|+]` |

可组合。wiki 的例子：

    Democratic party popularity: [?party_popularity@democracy|%G0]
    Modifier token value: [?modifier@my_modifier|.1%%+]
    Has more than [?var_name|Y] political power

## 三个关键限制

### 1. 小数最多 5 位

wiki 原文：

> Due to the nature of the game's variables, there are no more than 5 decimals that can be shown.

**这与静态分析得到的 `CFixedPoint` scale = `100000`（即 10^5）完全吻合 —— 两条独立证据互证。**

### 2. `SI` 只到 M（百万）

描述里只举了 K 和 M，**没有 G（十亿）或 T（万亿）**。

### 3. 没有补零修饰符

所以不能用 `[?lo]` 拼出固定宽度的低位数字。

## 值域（实测，与上一轮数据一致）

    set 0              -> "0"
    set 12             -> "12"
    set 1234567        -> "1234567"
    set 1234567890     -> "1234567890"
    set 2147483647     -> "2147483647"      上限
    set -2147483648    -> "--2147483648"    游戏自身显示 bug（双负号）
    set 1.5            -> "1.5"             支持小数

**上限就是 int32 的 `2147483647`**，与 `set_variable` 的存储位宽一致。

## 原版怎么显示超过百万的数

wiki 直接给出了原版做法 —— **拆成三个变量**：

    trillions  :  temp_display_T 加后缀 T
    billions   :  temp_display_B 加后缀 B
    millions   :  temp_display_M 加后缀 M

**=> 官方自己就是用「多个 32 位变量分档」表示大数的，不是靠单个变量。**
这印证了本项目自建 64 位变量时采用的「高低位 / 分档存储」方向。

## 对自建 64 位变量的启示

1. **显示层沿用原版思路**：把值按 T / B / M 分档写进几个游戏变量，本地化里用 `[?x_T|2]T` 拼。
2. **不需要补零**：分档显示是「每档各自显示」，不是定宽拼接。
3. **小数上限 5 位**：与 `EFF_FIXED_SCALE 100000` 一致，不要再提高精度。

## 相关文档

| 主题 | 文档 |
|---|---|
| 变量类型与上限 | `ai_docs/09_脚本数值系统/变量与定点数.md` |
| 自建 64 位变量 | `test/reports/20261010_2150_插件_自建64位变量effect_验证.txt` |
| 注册新 effect | `ai_docs/08_Effect系统/注册新Effect.md` |
