# 注册新 Effect — 运行期实测记录

> 历史阶段记录：全文的“本轮/当前/下一步”仅指当时实验，不是最新状态或可直接照抄的实施指令。现状见 [注册器API](注册器API.md)。旧方案、失败与旧偏移保留用于追溯，不覆盖现实现。

> 本页是《注册新Effect.md》的续篇，记录 2026-10-09 的运行期实测过程与结论。

## 五、运行期实测记录（2026-10-09）

### 环境就绪确认

    hoi4 base = 0x7ff6f3cc0000
    lexer initialized (0x1435E1AB0)       = 1     ✓
    lexer sync initialized (0x1435E1AB1)  = 1     ✓
    dyn count (dword_1435E1ACC)           = 50280   ← 游戏自己已注册 5 万个
    dyn data  (qword_1435E1AC0)           = 0x211d0d73040
    name table(qword_1435E1AE0)           = 0x2116f34d040

**50280 这个数字本身就是证据**：游戏运行到进地图时，已动态注册了 5 万个 token。

### 注册测试

    AddDynamicToken("set_camera_height")
      out_id = 70279

**新 id 的算法**：`70279 = 50280(count) + 1 + 19998(base)`

### 验证（三项全过）

| 验证 | 结果 |
|---|---|
| token 真的进表（用 id 反查名字） | `id 70279 -> "set_camera_height"` ✓ |
| id 递增 | 再注册 `my_test_token_xyz` 得到 70280 ✓ |
| 幂等 | 重复注册 `set_camera_height` 仍返回 70279 ✓ |

注册期间游戏进程存活（pid 50684，4571 MB）。

### 调用方式（Frida 原型）

    // 注意: IDA 里给的地址是绝对地址(基址 0x140000000), 必须换算成 RVA
    //       这是本次踩过的坑 —— 直接 base.add(0x1435E1AB0) 会算到模块外
    function img(ea) { return Process.getModuleByName('hoi4.exe').base.add(ea - 0x140000000); }

    const outId = Memory.alloc(8);
    const strBuf = Memory.allocUtf8String('set_camera_height');
    const view = Memory.alloc(16);          // { char* data; size_t len }
    view.writePointer(strBuf);
    view.add(8).writeU64(name.length);
    new NativeFunction(img(0x1424BB460), 'pointer', ['pointer','pointer','pointer'])(outId, view, ptr(0));

探针：当轮_addtoken.js（旧名称）；现有对应探针为`test/modules/effect/effect_add_token.js`

## 六、还剩什么

| 步骤 | 状态 |
|---|---|
| 1 注册 token 名字 | **✓ 已完成并验证** |
| 2 构造 entry + 工厂虚表 | 待做 |
| 3 构造实例 + 执行虚表 | 待做 |
| 4 注册进 `_EffectEntries` | 待做 |
| 5 触发并验证设置了摄像头高度 | 待做（最终标准） |
## 七、成功记录（2026-10-09 18:47）

### 结果

    触发前:  +0x69C(目标高度)=310.00   +0x678(当前高度)=310.04
    控制台:  event camtest.1  ->  ok=1  "Executed #44600001"
    触发后:  +0x69C(目标高度)=1500.00  +0x678(当前高度)=1499.86
    执行日志:[18:47:04.888] [eff] exec#1 setcamheight 1500  310.00 -> 1500.00

**摄像头高度 310 -> 1500，由注入的 effect 造成。**

### 实现的关键取舍：不猜任何签名

| 需要 | 做法 |
|---|---|
| 实例虚表 25 槽 | **从 `CAddStabilityEffect` 的虚表整体复制**，只换 `+0x68`。其余 24 槽是游戏自己的实现 |
| 实例布局 | **不自己构造**，直接调游戏工厂 `sub_14033C420` 造，再把虚表指针换掉 |
| entry 虚表 | `[0]` 借用游戏的析构，`[1]` 用我们的工厂 |
| 执行逻辑 | 复用已实证的 `sub_1412643F0`（`Camera_SetHeight`） |

**这样从头到尾没有猜过任何结构布局或函数签名。**

### 时序：注册必须抢在脚本解析之前

    18:45:23.486  [plugin] thread start
    18:45:25.732  [plugin] lexer ready at poll 212     ← 2.2 秒就绪
    18:45:25.732  [eff] registered tokenId=20052
    18:45:36.360  [plugin] Camera_RegisterCommands

第一版把注册放在「等 CGameState」之后（14 秒），结果脚本已解析完：

    error.log: [effect.cpp:445] Invalid effect 'set_camera_height'
    error.log: Unknown effect-type: set_camera_height, near line: 9

提前到线程最前面（10ms 密集轮询）后，该错误消失。

### 本轮踩的坑

| 坑 | 说明 |
|---|---|
| A | **IDA 地址是绝对地址**，必须减 `0x140000000` 换成 RVA；否则 `access violation` |
| B | **Frida 的 `Memory.alloc` 随脚本卸载释放**；跨会话验证不成立 → 实现必须放 DLL |
| C | **注册时序**（见上） |
| D | 宏重定义 `RVA_CAM_SLOT`/`RVA_CAM_SETH`；补 `#include "camera_height.h"` |

### 测试用文件

    events/zz_camtest.txt                      触发用事件
    localisation/zz_camtest_l_english.yml
    test/lib/exec_console_command.js                进程内执行控制台命令
    test/probes_frida/_trigger_event.py

### 尚未完成

**执行函数目前写死 1500，没有读取 effect 的参数。**
即 `set_camera_height = 999` 也会设成 1500。

`add_stability` 的执行（`sub_14034C2F0`）是从 `this+0x58` 取参数的：

    sub_140544C90(a1 + 88, &v6, a2, 0, 0);   // this+0x58 -> v6
    return sub_1406D23F0(v4, v6);            // v6 是 64 位定点

但 `sub_140544C90` 的签名与 `v6` 的单位都未实证。
## 八、参数生效（2026-10-09 18:55）

### 结果

    事件          参数      ok     摄像机 +0x69C      判定
    camtest.1   1500    = 1    1500.00           OK
    camtest.2   999     = 1    999.00            OK
    camtest.1   1500    = 1    1500.00           OK
    camtest.2   999     = 1    999.00            OK

**参数真的生效，不再写死。**

### 参数在哪：用运行时对比 dump 确定，不猜

做法：同一个 effect 传两个不同值（1500 / 999），dump 实例前 `0x140` 字节，对比差异。

| 偏移 | 调用#1（1500） | 调用#2（999） | 解读 |
|---|---|---|---|
| `+0x108` | `0x30303531` | `0x00393939` | 小端 = `"1500"` / `"999\0"` |
| `+0x118` | `4` | `3` | 字符串长度 |
| `+0x120` | `0x0F` | `0x0F` | capacity = 15 = SSO |

**正是 MSVC `std::string` 布局**：

    +0x108 : union { char[16]; char* }   数据（SSO 内联）
    +0x118 : size_t size                 长度
    +0x120 : size_t capacity             容量（<=15 用内联）

**结论：effect 参数以字符串形式存放，由 effect 自己解析。**

实现里处理了 SSO 与堆指针两种情况，并自己做了 atof。

### 同时变化但不是参数的字段（仅记录，未采用）

| 偏移 | #1 | #2 |
|---|---|---|
| `+0x030` | 9 | 19 |
| `+0x098` | `08F0D180` | `05F45A60` |
| `+0x128` | `43A9618B` | `4EC764E9` |
