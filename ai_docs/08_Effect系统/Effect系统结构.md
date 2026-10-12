# Effect 系统的结构

> 历史阶段记录：全文的“本轮/当前/下一步”仅指当时实验，不是最新状态或可直接照抄的实施指令。现状见 [注册器API](注册器API.md)。旧方案、失败与旧偏移保留用于追溯，不覆盖现实现。

> 依据：IDA 9.0 对 hoi4.exe 1.19.3 的静态分析（2026-10-09）
> 探针：test/probes_ida/vtable/_eff_*.py

## 与控制台指令完全不同的机制

| | 控制台指令 | **Effect** |
|---|---|---|
| 注册表形态 | **数据表**（`qword_14332F4F8`，元素 456 字节） | **`std::map<int, entry*>`**（`qword_143330000`） |
| 分发方式 | 查表拿函数指针直接调 | **查表拿 entry → 调工厂造实例 → 调实例虚函数** |
| 是否有虚表 | 无 | **有，两层** |

所以 effect 不能像控制台指令那样「填个结构体就注册」，
它需要提供 **C++ 对象 + 虚表**。

## 三层结构

```
脚本 effect 名  --解析-->  token id (int)
                              |
                     _EffectEntries  (std::map)      qword_143330000
                              |
        entry->vftable[+0x08]()   即工厂函数
                              |
                        effect 实例 (如 CAddStabilityEffect)
                              |
        写参数: 实例+0x2C = 值, 实例+0x34 = 1
                              |
        实例->vftable[+0xA8]()   即【执行】
```

## 关键地址

| 名称 | 地址 | 说明 |
|---|---|---|
| `_EffectEntries` | `qword_143330000` | 全局 `std::map<int, CEffectEntryBase*>` |
| 注册 entry | `sub_1405415A0(map, id, entry)` | 往 map 插入 |
| 解析/分发 | `sub_140540EE0` | 按 token 查 map → 造实例 → 执行 |
| 注册名字 | `sub_1424C4B70(slot, id, name)` | 写 `{id, name}` 到 72 字节的槽 |

## 一次典型注册（add_stability）

注册函数的反编译：

    __int64 sub_1400188E0()
    {
      v0 = qword_143330000;                    // _EffectEntries
      if ( !v0 ) { sub_14053D840(); v0 = qword_143330000; }
      v1 = malloc(0x10);                       // entry 只有 16 字节
      v1[1] = "Adds the stability to the country in scope. Example: add_stability = 5";
      *v1   = &CEffectEntry<CAddStabilityEffect>::`vftable';
      return sub_1405415A0(v0, 10005LL, v1);   // id = 10005
    }

**entry = `{ vftable*, 描述字符串* }`，只有 16 字节。**

## entry 的虚表（`CEffectEntry<CAddStabilityEffect>` @ 0x14277CED8）

| 槽 | 函数 | 作用 |
|---|---|---|
| `+0x00` | `sub_1402E2FF0` | 析构 |
| **`+0x08`** | **`sub_14033C420`** | **工厂：造实例** |
| `+0x10` | （RTTI 数据） | |

工厂的反编译：

    _QWORD *sub_14033C420()
    {
      v0 = malloc(0x128);                      // 实例 296 字节
      sub_14053CFD0(v0);                       // 基类构造
      *v1 = &CValueEffect::`vftable';
      sub_14014AFD0(v1 + 11);
      *v1 = &CAddStabilityEffect::`vftable';   // 换成最终虚表
      return v1;
    }

## 实例的虚表（`CAddStabilityEffect` @ 0x14276EDF8）

| 槽 | 函数 | 大小 |
|---|---|---|
| `+0x00` | `sub_1402E4100` | 64 |
| `+0x08` | `sub_14053FF00` | 155 |
| `+0x10` | `sub_140177730` | 9 |
| `+0x18` | `sub_14139A5D0` | 498 |
| `+0x20` | **`sub_140540EE0`** | **1726** ← 解析器本体（见下） |
| `+0x28` | `sub_1401807B0` | 3 |
| `+0x30` | `sub_141392D30` | 145 |
| `+0x38` | `sub_140378500` | 533 |

## 执行是怎么被调到的

`sub_140540EE0`（effect 解析/分发）的核心：

    // 按 token 在 _EffectEntries 里做二叉搜索
    v9 = qword_143330000;
    while ( !*((_BYTE *)v11 + 25) ) {
      if ( *((_DWORD *)v11 + 8) >= token ) { v12 = v11; v11 = *v11; }
      else                                    { v11 = v11[2]; }
    }
    ...
    // 命中后：
    v14 = (*( (v12 + 40) + 8 ))(*(v12 + 40));   // entry->vftable[1]()  工厂
    *(v14 + 44) = *sub_1424BF5B0(a2, &v58);     // 参数值 -> 实例+0x2C
    *(v14 + 52) = 1;                            // 实例+0x34 = 1
    // 执行
    if ( !(*(**(v55) + 168))(v55, v4) ) { ... 报错 ... }
                                        ^^^ 168 = 0xA8 = 实例虚表第 21 个槽

**所以「执行」在实例虚表的 `+0xA8`。**

## 其它有用的副产品

- 反编译里泄漏了源码路径：`C:\mnt\gsg\hoi4\hoi4_merged\hoi4\source\effects\effect.cpp`
- 断言文本：`_EffectEntries.find( Token ) == _EffectEntries.end()`（重复注册会断言）
- 特例 token：`14573` 与 `14035` 是 `if` / `else if`，走 `CIfEffect` 分支
- `qword_143330000` 被引用 **1128** 处 —— 每个 effect 一个注册函数

## 尚未确定的部分

| 问题 | 影响 |
|---|---|
| 实例虚表 `+0xA8` 的函数签名 | 决定了我们的执行函数怎么写 |
| 参数怎么从脚本传进来 | effect 的值（如 `= 500`）落在实例 `+0x2C`，但单位/类型未知 |
| 名字→token 的注册表结构 | 决定能不能加新名字 |
| id 的取值范围 | 不能与现有冲突 |
| 注册时机 | 必须在 `_EffectEntries` 建好之后、脚本解析之前 |
## 已确证 vs 未确证（诚实清单）

### 已确证

| 事实 | 证据 |
|---|---|
| `_EffectEntries` 是 map | `sub_1405415A0` 是红黑树插入；断言文本 `_EffectEntries.find( Token ) == _EffectEntries.end()` |
| entry = 16 字节 `{vftable*, desc*}` | `sub_1400188E0` 的 `malloc(0x10)` + 两处赋值 |
| entry 虚表 `+0x08` = 工厂 | `sub_14033C420` 里 `malloc(0x128)` + 设 `CAddStabilityEffect::vftable` |
| 实例 296 字节，虚表 25 槽 | `malloc(0x128)`；虚表从 `0x14276EDF8` 读到 25 个有效槽 |
| 参数落在实例 `+0x2C` | `*(v14 + 44) = *sub_1424BF5B0(a2, &v58)` |
| 实例 `+0x34` 被置 1 | `*(v14 + 52) = 1` |
| `sub_140540EE0` 是按 token 分发 | 红黑树按 `*(node+32)` 做 key 比较 |
| `if`/`else if` 是特例 token | `token == 14573 \|\| token == 14035` 走 `CIfEffect` 分支 |

### 未确证（不要当成已知）

| 问题 | 现状 |
|---|---|
| **「执行」在哪个虚表槽** | `+0x18` 经核实是**参数校验**（constructing `"Not a valid value: "`），不是执行 |
| **执行的函数签名** | 不知道 |
| **执行是何时被触发的** | `sub_140540EE0` 只是把实例存进 `a1+8` 容器（`sub_1401205A0`），说明是「先收集后执行」，触发点还没找到 |
| 名字 → token 的注册表结构 | 只看到 `sub_1424C4B70(slot, id, name)` 写 72 字节的槽，槽被谁读还没查 |
| id 的取值空间 | 不知道上限，也不知道能不能自选 |

### 走过的一个弯路

我一度把实例虚表的 `+0xA8`（`sub_14053D7F0`）当成执行，
反编译后才发现它是 **scope 掩码校验**：

    bool sub_14053D7F0(a1, a2)
    {
      return !a2 || !(...(*a1 + 152))(a1) || (((...(*a1 + 152))(a1) & a2) != 0);
    }

**教训**：靠「函数大小像不像」猜语义不靠谱，必须读代码。
## 虚表逐槽比对的结果（把猜测逐个排除）

对比 `CValueEffect`（基类，`0x14273D140`，28 槽）与 `CAddStabilityEffect`（子类，25 槽），
**只有 4 个槽被重写**：

| 槽 | 偏移 | 基类 | 子类 | 实为何物 |
|---|---|---|---|---|
| 7 | `+0x38` | `sub_1401773F0`(34B) | `sub_140378500`(533B) | **序列化**（生成 `"EFFECT_ADD_STABILITY ..."` 文本） |
| 13 | `+0x68` | `sub_14053E130`(94B) | `sub_14034C2F0`(87B) | 未查 |
| 19 | `+0x98` | `GetCommonButt...` | `sub_1402E30E0`(6B) | 未查 |
| 20 | `+0xA0` | `sub_1401776F0`(6B) | 6 字节小函数 | 未查 |

## 试错记录（务必看，避免重复走）

我把三个槽误判成「执行」，逐个反编译后都排除了：

| 我以为 | 实际 | 怎么排除的 |
|---|---|---|
| `+0xA8`（`sub_14053D7F0`, 73B） | **scope 掩码校验** | 反编译见 `(... & a2) != 0` |
| `+0x18`（`sub_14139A5D0`, 498B） | **参数值校验** | 反编译见构造 `"Not a valid value: "` 并报错 |
| `+0x38`（`sub_140378500`, 533B） | **序列化**（写回脚本文本） | 反编译见 `"EFFECT_ADD_STABILITY"` 字面量 |

**教训：不能靠「函数大小像不像执行」来猜，必须读代码。**
三次猜测都错了，每次都要花一轮反编译来纠正。

## 关于「执行在哪」的当前判断

`sub_140540EE0` 的完整流程：

1. 按 token 在 `_EffectEntries` 里做红黑树查找
2. 命中则 **`entry->vftable[+0x08]()`** 造实例
3. `*(实例 + 0x2C) = 参数值`，`*(实例 + 0x34) = 1`
4. scope 校验（实例 `vftable[+0xA8]()`）
5. **`sub_1401205A0(a1 + 8, &instance)`** —— push 进 `CPdxArray`
6. 调 `vftable[+0x18]()` 做参数校验

**第 5 步是关键：实例被「收集」进一个数组就返回了。**
所以执行必然是**另一个函数遍历那个数组**时发生。

`a1 + 8` 是 `sub_140540EE0` 第一个参数的成员，而该函数被引用 306 处
（各 effect 的解析函数都会调到它），说明 `a1` 是某种「effect 列表」上下文。

**下一步要查的是：谁遍历 `a1+8` 那个数组。**
## ★ 执行机制（已确证）

### 结论

| 位置 | 作用 |
|---|---|
| 实例虚表 **`+0x60`** | `sub_14053D9E0`（1865B）通用骨架：gamestate 断言 + scope 处理 |
| 实例虚表 **`+0x68`** | **★★★ 真正的「执行」** |

**执行签名**：`void __fastcall Execute(effect* this, Scope* scope)`

### 证据一：基类 `+0x68` 是「遍历子 effect」

    __int64 __fastcall sub_14053E130(__int64 a1, __int64 a2)   // CValueEffect::?
    {
      i_1 = *(int *)(a1 + 20);                             // this+0x14 = 子 effect 数量
      if ( i_1 > 0 )
        for ( i = 0; i < i_1; ++i )
        {
          v6 = *(_QWORD *)(*(_QWORD *)(a1 + 8) + 8 * i);   // this+0x08 = 子 effect 数组
          result = (*(**(v6) + 96))(v6, a2);               // 调子 effect 的 +0x60
        }
    }

说明 `this+0x08` 就是 `sub_140540EE0` 里 push 进去的那个 `CPdxArray`。

### 证据二：`CAddStabilityEffect` 重写的 `+0x68` 真的在改 stability

    __int64 __fastcall sub_14034C2F0(int a1, __int64 a2)
    {
      v3 = a2;
      v4 = sub_140BB4390(a2 + 8);              // 从 scope 取 CCountry
      sub_140544C90(a1 + 88, &v6, v3, 0, 0);   // 从 this+0x58 取参数值
      return sub_1406D23F0(v4, v6);            // 改 stability
    }

而 `sub_1406D23F0` 就是 stability 的写入口：

    __int64 __fastcall sub_1406D23F0(__int64 a1, __int64 a2)
    {
      v2 = a2 + *(_QWORD *)(a1 + 4304);        // CCountry+0x10D0，累加
      *(_QWORD *)(a1 + 4304) = v2;
      ... 夹紧到 [qword_143332E98, qword_143332DF8] ...
    }

**stability 是 64 位定点数，存在 `CCountry+0x10D0`。**

### 一个反直觉的点

子类 `+0x68` **没有**调基类去遍历子 effect，它直接做自己的事。
而基类 `+0x68` 只负责遍历子 effect 并调它们的 `+0x60`。

所以这两个槽的分工是：

- `+0x68`：本 effect 的「执行」（子类覆盖；想处理子 effect 得自己调基类或遍历）
- `+0x60`：被父 effect 遍历时被调用的入口（通用骨架，一般不覆盖）

### 至此，注册新 effect 需要的东西都齐了

| 需要提供 | 内容 |
|---|---|
| entry 对象（16 字节） | `{ 我的 entry 虚表*, 描述字符串* }` |
| entry 虚表 | `[0]` 析构、`[1]` **工厂**（造实例） |
| 实例对象（296 字节） | 布局对齐 `CValueEffect`（子 effect 数组在 `+0x08`、参数在 `+0x58`） |
| 实例虚表 | 25 槽；**`+0x68` 写我们的执行**；其余可指向基类实现 |
| 注册 entry | `sub_1405415A0(qword_143330000, 新id, entry)` |
| 注册名字 | `sub_1424C4B70(名字槽, 新id, "set_camera_height")` ← **槽的结构待查** |
