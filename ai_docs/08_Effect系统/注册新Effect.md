# 注册新 Effect 的完整方案

> 依据：IDA 9.0 对 hoi4.exe 1.19.3 的静态分析（2026-10-09）
> 探针：test/probes_ida/vtable/_tok*.py、_dyn*.py、_lex*.py、_eff_*.py

## 结论：可行，一共四步

| 步骤 | 调用 | 作用 |
|---|---|---|
| 1 | `sub_1424BB460(&id, &nameView, 0)` | **注册 token 名字，拿到新 id** |
| 2 | 自己构造 **entry**（16 字节） | `{ entry虚表*, 描述* }`，虚表 `[+0x08]` = 工厂 |
| 3 | 自己构造**实例 + 虚表** | 执行写在虚表 **`+0x68`** |
| 4 | `sub_1405415A0(qword_143330000, id, entry)` | 把 effect 注册进 `_EffectEntries` |

## 一、token 表（名字 ↔ id）

### 静态表（编译期生成）

| 项 | 值 |
|---|---|
| 表首 | `0x14338D170` |
| 元素大小 | **72 字节** |
| 元素个数 | **10765** |
| 表尾 | `0x14344A518` |
| 元素布局 | `{int id @+0, byte @+4, 字符串对象 @+8}` |

验证方式（两条独立路径一致）：

    sub_142703050: eh vector destructor iterator(&unk_14338D170, 0x48, 0x2A0D, ...)
    (0x14344A518 - 0x14338D170) / 72 = 10765

源码出处：`builddir/generated/hoi4_tokens.cpp`（断言文本里写着）。

查找函数：

    char *sub_14206CDC0(int id)     // 按 id 线性查找，返回 72*index 处
    char *sub_14206CE70(int index)  // 按索引直接取

注意 **id ≠ 索引**：`add_stability` 的槽是 `0x1433A7630`（索引 1496），而它的 id 是 **10005**。

### 动态表（运行时可增长）★ 关键

| 变量 | 含义 |
|---|---|
| `qword_1435E1AC0` | 动态 token 数组 data |
| `dword_1435E1ACC` | count |
| `qword_1435E1AE0` | **token 名字表**（32 字节/项） |
| `byte_1435E1AB0` | 已初始化标志 |
| `qword_1435E1AD0` | 分配器 |
| `unk_1435E1AD8` | 互斥锁 |
| `unk_1430C6DD8` | **哈希表（名字 → 索引）** |

## 二、AddDynamicToken（注册 token 的 API）

### 高层封装

    int *__fastcall sub_1424BB460(int *out_id, __int128 *name, __int64 a3)
    {
      if ( !byte_1435E1AB1 ) { ... "Trying to add dynamic token before lexer is
                                    synchronized initialized" ... lexer.cpp:241 ... }
      v6 = *name;                                // 拷贝 16 字节
      sub_1424BB500(out_id, (char **)&v6, a3);
      return out_id;
    }

### 底层实现

    int *__fastcall sub_1424BB500(int *out_id, char **name, __int64 a3)

**参数**：

| 参数 | 类型 | 说明 |
|---|---|---|
| `out_id` | `int*` | 输出新 token 的 id；失败时写 0 |
| `name` | `char**` | 名字；`name[1]` 是长度，`*name` 是数据 |
| `a3` | `__int64` | 位置信息（用于报错） |

**约束**（都有断言文本佐证，来自 `lexer.cpp`）：

| 行号 | 断言 |
|---|---|
| 174 | `Trying to add dynamic token before lexer is initialized` |
| 180 | `Trying to add empty dynamic token.` |
| 188 | `Creation of dynamic token "..." failed, keywords may not start with a digit or '-'` |
| 241 | `Trying to add dynamic token before lexer is synchronized initialized` |

**所以名字不能为空、不能以数字或 `-` 开头。**

### 内部流程（反编译）

    sub_1424EDD20(&unk_1435E1AD8);            // 加锁
    sub_1424BAE40(&unk_1430C6DD8, &node, name);   // 哈希查找
    if ( node == 表尾 )                        // 未命中 → 新 token
    {
      n668 = count + 1 + base;                 // ★ 新 id 的算法
      if ( count == capacity )
      {
        capacity *= 1.5;
        newdata = allocator->alloc(72 * capacity, 8);
        sub_1424C4C00(newdata + 72*count, n668, &name);   // 构造 token 对象
        ... 复制旧数据 ...
        qword_1435E1AC0 = newdata;
      }
    }

### ★ 决定性证据：游戏自己在用

`sub_1424BB500` 只有 4 个调用者，全在游戏自己的代码里：

    sub_1424BB460   ← 高层封装
    sub_1424BC310   ← CLexer 读 token 时（脚本里出现未知字就动态加）
    sub_1424BE050
    (数据段一处)

**说明「运行时注册新 token」是 HOI4 原生支持的行为**，不是外挂式的硬塞。

## 三、Effect 注册

### `_EffectEntries`

| 项 | 值 |
|---|---|
| 全局 | `qword_143330000` |
| 类型 | `std::map<int, CEffectEntryBase*>` |
| 插入 | `sub_1405415A0(map, id, entry)` |
| 断言 | `_EffectEntries.find( Token ) == _EffectEntries.end()` |
| 源码 | `source/effects/effect.cpp:83` |

### 一次典型注册（`add_stability`）

    __int64 sub_1400188E0()
    {
      v0 = qword_143330000;
      v1 = malloc(0x10);                        // entry 只有 16 字节
      v1[1] = "Adds the stability to the country in scope. ...";
      *v1   = &CEffectEntry<CAddStabilityEffect>::`vftable';
      return sub_1405415A0(v0, 10005LL, v1);    // id = 10005
    }

### entry 虚表（`CEffectEntry<T>`）

| 槽 | 作用 |
|---|---|
| `+0x00` | 析构 |
| **`+0x08`** | **工厂：造实例** |

    _QWORD *sub_14033C420()                      // add_stability 的工厂
    {
      v0 = malloc(0x128);                        // 实例 296 字节
      sub_14053CFD0(v0);                         // 基类构造
      *v1 = &CValueEffect::`vftable';
      sub_14014AFD0(v1 + 11);
      *v1 = &CAddStabilityEffect::`vftable';
      return v1;
    }

### 实例虚表（25 槽）关键位置

| 偏移 | 作用 |
|---|---|
| `+0x08` | 取名字（`sub_14053FF00`） |
| `+0x18` | 参数值校验（构造 `"Not a valid value: "`） |
| `+0x20` | 解析（`sub_140540EE0`） |
| `+0x38` | 序列化（写 `"EFFECT_ADD_STABILITY"`） |
| `+0x60` | 通用执行骨架（`sub_14053D9E0`） |
| **`+0x68`** | **★ 真正的「执行」** |
| `+0xA8` | scope 掩码校验（`sub_14053D7F0`） |

### 执行签名与实例布局

    void __fastcall Execute(effect* this, Scope* scope);

`CAddStabilityEffect` 的实现：

    __int64 __fastcall sub_14034C2F0(int a1, __int64 a2)
    {
      v4 = sub_140BB4390(a2 + 8);              // 从 scope 取 CCountry
      sub_140544C90(a1 + 88, &v6, a2, 0, 0);   // 从 this+0x58 取参数
      return sub_1406D23F0(v4, v6);            // 改 stability（CCountry+0x10D0）
    }

实例布局（从基类构造推）：

| 偏移 | 含义 |
|---|---|
| `+0x08` | 子 effect 数组（`CPdxArray`：`{T** @+0, int cap @+8, int count @+0xC}`） |
| `+0x14` | 子 effect 数量 |
| `+0x20` | token id |
| `+0x2C` | 参数值 |
| `+0x34` | 标志（置 1） |
| `+0x58` | 参数区（`sub_140544C90` 从这里取） |

## 四、对本项目（设置摄像头高度）的映射

我们的执行函数应该写成：

    void __fastcall Exec_SetCameraHeight(MyEffect* this, Scope* scope)
    {
      float h = 取参数(this);                     // 从 this+0x58 附近
      void* cam = CamObj();                       // 复用已有逻辑
      if (cam) Camera_SetHeight(cam, h);          // 复用已实证的 setter
    }

**已有的 `Camera_SetHeight`（调 `sub_1412643F0`）可以直接复用。**
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

探针：`test/probes_js/_addtoken.js`

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
    test/probes_js/_exec_cmd.js                进程内执行控制台命令
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
## 九、本地化文本（2026-10-09 19:13）

### 现象

游戏里我们的 effect 显示成了 `"增加基础稳定度：+150000.00%。"`，
参数 1500 被当百分比放大成 150000.00%。

### 三个根因

| # | 根因 |
|---|---|
| 1 | **实例虚表 `+0x38` 没被覆盖**。它是「生成工具提示文本」的虚函数；`CAddStabilityEffect` 的实现 `sub_140378500` 里硬编码 key `"EFFECT_ADD_STABILITY"` |
| 2 | 该模板是 `EFFECT_ADD_STABILITY: "增加基础稳定度：$VAL|+=%$。"`，`$VAL|+=%$` 会把值按百分比显示 |
| 3 | **自写的本地化文件缺 UTF-8 BOM**，游戏拒绝加载 |

### 修复

**1) 覆盖 `+0x38`**

    g_execVt[0x38 / 8] = (void*)MyGetTooltip;

实现要点（只换 key，其余照抄游戏逻辑）：

    ((PackKeyFn)(img + 0x2245E60))(packed, "EFFECT_SET_CAMERA_HEIGHT", NULL, 0);
    ((FormatFn )(img + 0x10E48A0))(fin, ctx, packed);
    把 fin 拷到 out，再追加 '\n'

**必须用游戏自己的 `sub_142245E60` 打包**。
我第一版用自写的 `Wstr` 构造 `packed` 再调 `sub_1410E48A0`，会 access violation `0xffffffffffffffff`。

**2) 本地化文件（UTF-8 **带 BOM**）**

    localisation/english/zz_camtest_l_english.yml
      l_english:
       EFFECT_SET_CAMERA_HEIGHT: "Set camera height."

    localisation/simp_chinese/zz_camtest_l_simp_chinese.yml
      l_simp_chinese:
       EFFECT_SET_CAMERA_HEIGHT: "设置摄像机高度。"

注意：语言目录必须放在 `localisation/<lang>/` 下（放 `localisation/` 根下不行）。

缺 BOM 时 error.log 会说：

    [localize.cpp:1639]: Localization file '...' should be in in utf-8-bom encoding
    [pdx_localize.cpp:1031]: Missing UTF8 BOM in ...

### 验证

    [efftip] call#1 packed=[设置摄像机高度。] sz=24 cap=31
    [efftip] call#1 formatted=[设置摄像机高度。]
    [efftip] call#1 key=EFFECT_SET_CAMERA_HEIGHT len=24 text=[设置摄像机高度。]

三条都是「设置摄像机高度。」；error.log 无 camtest 错误；摄像头仍正确 310 -> 1500。

### 参数显示（2026-10-09 19:32）

文本改为 `设置摄像机高度：$VAL$。`，参数用**原版的方式**取：

    long long fixed = 0;
    ((GetParamFn)(img + 0x544C90))((unsigned char*)self + 0x58, &fixed, ctx, 0, 0);
    // fixed = 150000000  (= 1500 x 100000, 定点)
    paramDesc[0x00] = 9;
    paramDesc[0x08] = img + 0x2745A00;
    paramDesc[0x50] = fixed;
    sub_142245E60(packed, "EFFECT_SET_CAMERA_HEIGHT", paramDesc, 1);
    sub_1410E48A0(fin, ctx, packed);

结果：`设置摄像机高度：1500.00。`

**关键坑：实例 `+0x108` 在「工具提示」阶段是空的（`sz=0`），只有执行阶段才有值。**
所以工具提示必须走 `sub_140544C90(self+0x58)`。

| 阶段 | `+0x108` | 正确来源 |
|---|---|---|
| 执行（`+0x68`） | `"1500"` 有值 | 两者都行 |
| 工具提示（`+0x38`） | **空** | **只能 `sub_140544C90(self+0x58)`** |
### 顺便修掉的探针缺陷

`ready()` 的就绪门槛原本是 `h > 0.0`，太松 —— 游戏没进地图时 `h` 可能是 0。
改成 `50 <= h <= 3000`（摄像机自身的最小/最大值），
否则 `country_event` 会报 `Target ID is invalid.`（没有玩家国家）。
