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
      void* cam = Camera_GetObject();            // 复用已有逻辑
      if (cam) Camera_SetHeight(cam, h);          // 复用已实证的 setter
    }

**已有的 `Camera_SetHeight`（调 `sub_1412643F0`）可以直接复用。**
