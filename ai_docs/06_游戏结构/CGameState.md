# CGameState 布局

> 依据：IDA 静态分析 + 运行时实测
> 全局槽：hoi4.exe + 0x332F260

## 全局

*(hoi4.exe + 0x332F260) 就是 CGameState*（也写作 CCurrentGameState）。
**它由 NULL 变非空，就是"游戏状态已建立"的硬信号**，比掐表可靠。

## 已确认的字段

| 偏移 | 类型 | 内容 |
|---|---|---|
| +0x2B0 | CProvince* | 省份数组（13414 个） |
| +0x2C8 | CState* | 州数组（1082 个） |
| +0x310 | CCountry** | 国家数组 |
| +0x318 | int | 国家数量（原版 440） |
| +0x328 | int | 9 |
| +0x340 | int | 474 |
| +0x358 | CCountryTag | tag 表 |
| +0x360 | int | tag 表数量 474 |
| +0x370 | | 440 x 8，值为 0x01010101 |
| +0x388 | int | 440 |
| +0x6A8 | | CCharacter 管理器 |

## 常用容器链

    CGameState + 0x310 -> CCountry**   (count 在 +0x318)
    CCountry   + 0x278 -> CFleet**     (count 在 +0x284)
    CFleet     + 0xB8  -> CTaskForce** (count 在 +0xC4)
    CCountry   + 0x290 -> CArmy**      (count 在 +0x29C)
    CShip      + 0x728 -> CTaskForce*

## 虚表 RVA（部分）

| 类 | RVA |
|---|---|
| CCurrentGameState 主 | 0x2721158 |
| CCurrentGameState 次 | 0x27211B0 |
| CCountry | 0x27E7360 |
| CState | 0x2936CC0 |
| CProvince | 0x2971B18 |
| CCharacter | 0x297EA60 |
| CArmy | 0x295A2B0 |
| CUnit | 0x29530D8 |
| CDecision | 0x27EB3D0 |
| CEffect | 0x27D4990 |
| CTrigger | 0x27D55F0 |

## 用户 verdict 提醒

类结构不能只靠虚表证明。**必须把名字和 id 找出来**才算数
—— 这是本工程被明确要求过的标准。
