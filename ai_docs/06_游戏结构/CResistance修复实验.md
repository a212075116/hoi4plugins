# CResistance 修复实验记录

> 该页是对应抵抗实验的结构/状态记录，不是当前模组配置快照；本次未重测抵抗模块或外部mod文件。实验中的待查项保持待查，不能据别的模块通过而标为解决。

> 本页是《CState与CResistance.md》的续篇，记录第六、七轮的尝试与结论。

### 第六轮：两条修复尝试都被否定

**尝试 A：删除全部 add_core_of**

把 393 个文件里的 753 行 add_core_of 全部删除后进图：

    删除前: resistance.cpp:609 = 435 条
    删除后: resistance.cpp:609 = 397 条

减少 38 条但不归零。**已回滚**（753 行、393 个文件均恢复，逐项核对一致）。

**尝试 B：给每个州补 1936.1.1 日期块形式的 controller**

注意 controller 的正确写法必须放在日期块里：

    history = {
        owner = WS1
        1936.1.1 = {
            controller = WS1
        }
    }

直接在 history 里裸写 `controller = X` 是不生效的（原版的 61 个例子全都写在日期块里）。
用正确写法给 446 个州都补上之后：

    resistance.cpp:609 = 435 条   (与未修改时完全相同)

**结论：controller 不是这条告警的成因。已回滚。**

### 一个必须记录的操作失误（已完全恢复）

回滚尝试 B 时，`Move-Item 备份目录 目标目录` 在目标目录仍存在的情况下会把源目录
**移成目标目录的子目录**；随后第二次 `Remove-Item -Recurse` 就把整个 states 目录删掉了。
所幸备份内容随之一起被移动、并未真正丢失：

    states/_states_backup_before_ctrl2/ 里 446 个文件完好
    -> 逐个 Move-Item 回到 states/，删除空子目录

恢复后逐项核对，与原状一致：

    文件数 446、总行数 15251
    严格匹配 ^\s*add_core_of\s*= 的行数 753、含它的文件数 393
    controller 出现 0 处

教训：**回滚前必须先确认目标路径不存在，或直接用复制而不是移动**；
`Move-Item` 到已存在目录不会报错，只会静默变成子目录，非常危险。
### 第七轮：抵抗自动启动开关 = should_initiate_resistance（官方文档确认）

官方 wiki（Effect 页面的 Resistance initiation triggers 一节）给出的规则：

    The behaviour of resistance being automatically initiated is decided by the
    `should_initiate_resistance` scripted trigger, by default defined in
    common/scripted_triggers/00_resistance_initiate_triggers.txt .
    If it is unfulfilled, the resistance will never initiate unless forced via the
    `force_enable_resistance` effect. Likewise, the resistance will always occur
    if it's true unless forcefully disabled.

命名规则：在默认触发器名后追加州 ID（下划线分隔）即可覆盖指定州：

    should_initiate_resistance_123_321 = { ... }   # 只作用于州 123 和 321

**极易踩的坑（官方原文）**：覆盖后【不会】自动沿用默认行为，必须在 else 分支显式再调一次，
否则该州的抵抗会无条件启动：

    should_initiate_resistance_123_321 = {
        if = {
            limit = { tag = ENG }      # 在 state scope 下, tag 就是占领者
            is_core_of = FRA
        }
        else = {
            should_initiate_resistance = yes   # 不写这句, 抵抗会无条件启动
        }
    }

### 单变量实测（针对 mod 的州 335，逐个条件分离）

探针写法：`should_initiate_resistance_<州ID> = { <单个条件> }`，
该州若仍进入抵抗系统说明条件为真。

| 探针 | 州 | 结果 | 结论 |
|---|---|---|---|
| `impassable = no` | 335 | 在列表 | 条件为 **TRUE** |
| `check_variable = { core_countries^num > 0 }` | 1 | 在列表 | 条件为 **TRUE** |
| `NOT = { is_core_of = FROM }` | 3 | 被排除 | 条件为 **FALSE**，即 `is_core_of = FROM` 为 TRUE |

把这三项按原版顺序组合起来（state-specific override 形式）时，州 335 被正确排除：

    should_initiate_resistance_335 = {
        impassable = no
        check_variable = { core_countries^num > 0 }
        NOT = { is_core_of = FROM }
    }
    # 结果: 州 335 不再进入抵抗系统

而磁盘上真正的默认 `should_initiate_resistance`（内容与上面一致）却让州 335 通过。
**两者内容相同、结果相反** —— 说明默认触发器的调用上下文里 `FROM` 与 state-specific
覆盖里的 `FROM` 不同（默认路径下 `is_core_of = FROM` 未能拦住核心区）。
这一点未继续深挖，由用户自行编写 mod 侧逻辑。

### 已验证可用的修复形式

两种都实测生效（州 335 从抵抗系统里消失）：

    # 形式一：彻底关掉该州的抵抗
    should_initiate_resistance_335 = { always = no }

    # 形式二：把原版逻辑显式写进该州的覆盖（保留正常判定、只是修正默认路径的行为）
    should_initiate_resistance_335 = {
        impassable = no
        check_variable = { core_countries^num > 0 }
        NOT = { is_core_of = FROM }
    }

### 与 flag208 的关系（修正第六轮的结论）

- `flag208` 只是「该州当前是否在抵抗系统里」的运行时标志，**它等于 0 并不代表该州没有抵抗**。
- 真正决定「该不该有抵抗」的是 `should_initiate_resistance`；`flag208` 是它的下游结果。
- `CResistance+0x2a0` 存放该州绑定的 `CScriptedTriggerTemplate`；未绑定时为
  `TNullObject<CScriptedTriggerTemplate>`（此时 `[vtbl+0x18]` 走默认分支返回 true）。
- 覆盖生效时 `+0x2a0` 会变成真正的 `CScriptedTriggerTemplate`。

### 本轮探针文件（留在 mod 里，供用户改写）

    mod/bakaifa/common/scripted_triggers/zz_probe_resistance_override.txt

实验当时记录该外部mod文件为默认should_initiate_resistance的完整覆盖；本次未核对当前外部文件内容，不把当时状态当现在配置。
