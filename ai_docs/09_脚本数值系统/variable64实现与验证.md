# variable64：实现与验证（第5~8轮）

> 上游：变量存储结构见《变量存储结构.md》，scope 与实例结构见《作用域与effect实例.md》。
> 本文记录从「借游戏机制读写变量」到「四条核心需求打通」的全过程与结论。
## 十九、四条核心需求全部打通（第8轮）

### 19.1 本轮完成的里程碑

| # | 需求 | 状态 | 证据 |
|---|---|---|---|
| 1 | 64 位数值化 | ✅ | 直接读写游戏变量槽的 8 字节 |
| 2 | 与 32 位运算兼容 | ✅ | 游戏读同一变量槽（会截断到 32 位） |
| 3 | 存档能存住 | ✅ | 它就是游戏变量，天然随存档 |
| 4 | log 能输出 | ✅ | 见下 |

### 19.2 log 读取实测

```
GVREAD v64gv = 789
GVREAD v64gv fmt = 789.00
GVREAD si = I789.00!
```

脚本：

```
log = "GVREAD v64gv = [?v64gv]"
log = "GVREAD v64gv fmt = [?v64gv|2]"
log = "GVREAD si = [?v64gv|SI]"
```

**`[?变量名]` 三种格式都能读到我们写入的值。**
注意 `[?v64gv]` 显示 `789` 而内部 raw 是 `78900000` —— **显示时会除以 100000**，
与定点语义一致。

### 19.3 完整链路

```
脚本: var64_set_a = 789
  │
  ├─ 我们读参数（sub_140544C90）-> raw = 78900000（定点 x100000）
  ├─ 造 CSetVariableEffect 实例（工厂 RVA 0x341F60）
  ├─ 变量名写到 inst + 200（CScopedVariable + 112）
  ├─ sub_140542280(inst + 88, scope, 0) -> 值地址
  └─ *(long long*)addr = raw
游戏侧:
  ├─ [?v64gv] 能读到 -> 789
  ├─ 随存档保存
  └─ 游戏系统也能读（32 位截断）
```

实测日志：

```
[var64] #2 set slot=a raw=78900000 value=789.00000
[var64] wrote name [v64gv] to 000001DA763FB908 (len=5)
[var64] wrote game var v64gv = 78900000 at 000001DA82E9E3F8
```

**两次写入落在同一个地址**（`0x1DA82E9E3F8`），说明变量被正确复用，不是每次新建。

### 19.4 语法实验结论

用三种形式调用 `var64_set_a` 的结果：

| 形式 | 结果 | 结论 |
|---|---|---|
| `var64_set_a = 789` | ✅ `raw=78900000` | **单值形式可用** |
| `var64_set_a = { var = dshprobe  value = 123 }` | ⚠️ 事件执行了，但 `raw=0` | **块被接受，但我们的参数描述读不到** |
| `var64_set_a = { dshprobe = 456 }` | ❌ 事件加载失败 | **简写形式是 `set_variable` 解析器专有的** |

### 19.5 剩余缺口

| 缺口 | 说明 |
|---|---|
| **变量名不可指定** | 当前固定为 `v64gv`。要实现原版语法需要块参数解析 |
| **块参数读不到** | 我们的参数描述（`self+0x58`，104 字节）只声明了单个值 |
| 数学表达式形式 | `{ 名字 = { value = X  multiply = 2 } }`，优先级最低 |

### 19.6 当前可用的能力（已实现并验证）

```c
/* src/plugin/SDK_RVA/variable64/variable64.c */

/* 造实例 + 取游戏变量值地址 */
int Var64_MakeGameVarInstance(void* scope, const char* name,
                               void** outInst, void** outAddr);

/* 直接用哈希表查（不依赖游戏函数） */
int Var64_LookupInScope(void* container, const char* name, long long* out);

/* FNV-1a */
unsigned int Var64_Fnv1a(const char* s);
```

已有的 effect：`var64_set_a` / `var64_add_a` / `var64_show_a` / `var64_diag`，
其中 `var64_set_a` **已经把值写进游戏变量 `v64gv`**（可通过 log 读取、随存档保存）。

## 二十、块参数的解析结果落在哪（第9轮 · 内存对比）

### 20.1 实验

同一 effect（`var64_set_a`），分别用两种形式调用，dump `self + 0x40 ~ 0x140`：

```
var64_set_a = 111                                    单值形式
var64_set_a = { var = dshprobe  value = 123 }        块形式
```

### 20.2 对比结果

| 偏移 | 单值形式 | 块形式 | 说明 |
|---|---|---|---|
| `+0x050` | `0xF` | `0xF` | 常量 |
| `+0x058` | `0x7FF6C87E8428` | 同 | 参数描述指针（常量） |
| **`+0x060`** | **`0x101`** | **`0x1`** | **标志位不同** |
| `+0x088` | `00004C1700000000` | 同 | 常量 |
| `+0x090` | `0x4C17`（19479） | 同 | 常量 |
| **`+0x098`** | **`0xA95F60` = 11100000** | **`0`** | **单值形式的定点值** |
| `+0x0C0` | `0x7FF6C9155170` | 同 | 常量 |
| **`+0x0C8`** | **`0`** | **`0x7B` = 123** | ★ **块形式的参数值** |
| `+0x0D0` | `0` | `0` | |
| `+0x0D8` | `0` | **`1`** | |
| `+0x0E0` | `0xF` | `0xF` | 常量 |
| `+0x108` | `0x313131` = `"111"` | `0x7B` = 123 | 数据区 |
| `+0x118` | **`3`** | **`1`** | 长度 |
| `+0x120` | `0xF` | `0xF` | cap |

### 20.3 结论

1. **块被游戏正常解析了**，值 123 出现在 `+0x0C8`
2. **单值形式的定点值在 `+0x098`**（`111 x 100000 = 11100000`）
3. **两种形式走的是不同的存储槽**，用 `+0x60` 的标志位区分：
   - 单值：`0x101`
   - 块：`0x1`
4. **块里的 `var = dshprobe` 没有出现在这一区间** —— 因为我们的参数描述只有一个槽，
   游戏只解析了第一个「值」，键名被忽略了

### 20.4 这带来一个可用的突破口

既然**块形式的值能在 `self + 0xC8` 读到**，我们只要：

```c
static long long Var64_ReadParamRaw2(void* self, void* scope)
{
    long long a = /* 老办法：self + 0x58 走 sub_140544C90 -> self+0x098 */;
    long long b = *(long long*)((unsigned char*)self + 0xC8);
    return (a != 0) ? a : b;
}
```

**就能同时支持两种形式。** 但变量名 `dshprobe` 仍然拿不到 ——
要拿到变量名，必须让参数描述容纳「命名子字段」，那是另一层工作。

### 20.5 下一步方向（第10轮）

| 方向 | 说明 |
|---|---|
| A. 让参数描述支持两个槽 | 逆向 `sub_140544C90` 的 `a4`/`a5` 参数，看能否按字段名取值 |
| B. 变量名改用固定前缀 + 数值后缀 | 用参数值本身编码名字（如 `v64_123`），绕开块解析 |
| C. 维持现状 | 单值形式 + 固定变量名，先把 64 位读写跑通（已可用） |

## 二十一、原版语法的实现路线（第10轮 · 关键实验）

### 21.1 目标

让 `set_variable64` 支持与 `set_variable` 完全相同的两种语法：

```
set_variable64 = { 名字 = 值 }
set_variable64 = { var = 名字  value = 值 }
```

### 21.2 实验一：换 entry 虚表

把 `var64_set_a` 的 `entryVt[0]` 换成 `CEffectEntry<CSetVariableEffect>` 的虚表（RVA `0x277C418`）。

结果：单值形式 `var64_set_a = 111` 报错

```
Error: "Non assign effect is not enclosed in {}: var64_set_a"
```

**说明 entry 虚表决定参数形态**（单值 vs 块）。

### 21.3 实验二：再换实例虚表

factory 造 `CSetVariableEffect` 实例（544 字节），并把实例虚表换成我们自己的（25 槽里 24 个取自
`CSetVariableEffect::vftable`，只把 exec 槽 `+0x68` 换成我们的函数）。

结果：exec 被正确调用了，但变量名不对：

```
[v64par] nameField(+200) size=1 ; nameField text = [{]
```

**游戏把块的 `{` 当成了变量名** —— 说明实例虚表也参与块内键的解析。

### 21.4 实验三：entryVt 的 patch 时机

`Effect_RegistryRegister` 内部会重设 `entryVt[0]`：

```c
def->entryVt[0] = *(void**)(img + RVA_STAB_ENTRY_VT);   // 覆盖我们之前的修改
def->entryVt[1] = (void*)def->factory;
```

所以必须在 `Effect_RegistryRegisterAll` **之后** patch。改到之后，patch 确实生效了
（`0x7FF6C63B2FF0` = RVA `0x2E2FF0`），但结果仍和实验二一样。

### 21.5 实验四（决定性）：完全复用游戏

注册一个 effect `var64_gm`，**entry 虚表、factory、实例虚表、exec 全部用游戏的**。

脚本：

```
set_variable = { gmprobe = 0 }
var64_gm = { var = gmprobe value = 555 }
log = "GMPROBE after = [?gmprobe]"
```

输出：

```
GMPROBE after = 555
```

**完全成功，没有任何错误。**

### 21.6 结论

| 项 | 结论 |
|---|---|
| entry 虚表 | 决定参数形态（单值 / 块） |
| 实例虚表 | 决定块内键的解析（换掉就会错乱） |
| **三者必须全部是游戏的** | **entry + 实例 + exec**，缺一不可 |

因此**不能**用一个「换了 exec 的实例」来继承游戏的块解析。

### 21.7 定下的实现路线：MinHook 挂 exec

```
1. set_variable64 的 entry / factory / 实例虚表 全部保持游戏的
   -> 块解析完全正确，变量名进 +200，参数进 +408

2. 在 factory 里给实例打标记（实例 +505 有 7 字节空隙未被构造函数使用）

3. 用 MinHook 挂 CSetVariableEffect::exec（RVA 0x364C60）
   - self+505 有标记 -> 我们的逻辑：
       sub_140542280(self+88, ctx, 0) 拿值地址
       写入完整 64 位
       返回
   - 无标记 -> 调原函数（set_variable 不受影响）
```

### 21.8 CSetVariableEffect 实例布局（本轮更新）

| 偏移 | 内容 |
|---|---|
| `+0` | 虚表（**必须是 CSetVariableEffect 的**） |
| `+88` | **CScopedVariable A** —— 变量名在 `+200`（= `+88 + 112`） |
| `+296` | **CScopedVariable B** —— 参数在 `+408`（= `+296 + 112`） |
| `+504` | byte 标志（exec 据它选分支） |
| `+505`..`+511` | 空隙（可用作标记） |
| `+512` | std::string（data `+512` / size `+528` / cap `+536`） |

构造函数 `sub_14032D260` 只初始化到 `+536`，所以 `+505`..`+511` 是安全空隙。

## 二十二、`set_variable64` 实现完成（第11轮 · MinHook 方案）

### 22.1 实现结构

```c
/* 1. 工厂：造游戏实例 + 打标记（实例 +505 有 7 字节空隙） */
static void* __fastcall Var64_GameSyntaxFactory(void)
{
    void* inst = Var64_PureGameFactory();          /* CSetVariableEffect 工厂，虚表保持游戏的 */
    *(unsigned*)((char*)inst + 505) = 0x53343656;  /* 标记 */
    return inst;
}

/* 2. 挂 exec（RVA 0x364C60） */
orig = InlineHook_Install(img + 0x364C60, (void*)Var64_GameSyntaxDetour);

/* 3. detour：查标记决定接管还是放行 */
static long long __fastcall Var64_GameSyntaxDetour(void* self, void* ctx)
{
    if (*(unsigned*)((char*)self + 505) == 0x53343656)
        return Var64_HandleGameSyntaxSet(self, ctx);
    return g_var64OrigGameSetExec(self, ctx);       /* 原版 set_variable 不受影响 */
}

/* 4. 接管逻辑：读名字、读参数、写 64 位 */
static long long __fastcall Var64_HandleGameSyntaxSet(void* self, void* ctx)
{
    /* 读参数（第二个 CScopedVariable = self + 296，第 5 参数传 1） */
    ((Var64GetParamFn)(img + 0x544C90))((char*)self + 296, &value, ctx, 0, (void*)1);
    /* 按名字取变量值地址（第一个 CScopedVariable = self + 88，名字在 +200） */
    addr = ((Var64LookupFn)(img + 0x542280))((char*)self + 88, ctx, NULL);
    *(long long*)addr = value;                      /* 写完整 64 位 */
}
```

### 22.2 注册要点

| 项 | 设置 |
|---|---|
| effect 名 | `set_variable64` |
| locKey | `EFFECT_SET_VARIABLE64` |
| `entryVt[0]` | **`CEffectEntry<CSetVariableEffect>` 的虚表**（RVA `0x277C418`），**必须在 `Effect_RegistryRegisterAll` 之后 patch** |
| `factory` | `Var64_GameSyntaxFactory` |
| 实例虚表 | **不动**（保持 CSetVariableEffect 的） |

### 22.3 实测结果

插件日志：

```
[hook] MinHook initialized
[eff] + set_variable64  tokenId=20163  loc=EFFECT_SET_VARIABLE64
[var64] set_variable64 entryVt=00007FF6C63B2FF0 factory=00007FFC1B428BA0
[hook] installed at 00007FF6C6434C60, orig=00007FF6C60C0FC0
[var64] gamesyntax hook installed
[var64] gamesyntax name=[v64a]
[var64] gamesyntax wrote 1234567890123400000 to 000001F973C97268
[var64] gamesyntax name=[v64b]
[var64] gamesyntax wrote 77700000 to 000001F973C98678
```

| 脚本 | 变量名 | 写入值 | 判定 |
|---|---|---|---|
| `set_variable64 = { var = v64a value = 12345678901234 }` | `v64a` | `1234567890123400000` | ✅ 完整 64 位 |
| `set_variable64 = { v64b = 777 }` | `v64b` | `77700000` | ✅ |

**两种语法全部工作，与原版 `set_variable` 完全一致。**

### 22.4 log 输出的截断规律（已精确定位）

游戏日志：

```
V64A log = 1942892530
V64B log = 777
```

验算：

```python
raw    = 1234567890123400000     # 槽里的完整值
value  = raw / 100000            # = 12345678901234
value % 2**32                    # = 1942892530   <-- 与 log 完全一致
```

**所以 `[?变量名]` 的输出 = `(raw / 100000) mod 2^32`** ——
先按定点比例还原成整数，再截断到 32 位。

| 判定 | 说明 |
|---|---|
| 槽里 | **完整 64 位**（已验证） |
| `[?var]` 显示 | 32 位（截断） |
| 小值（< 2^31） | 显示正确 |
| 大值 | 显示为低 32 位 |

### 22.5 全部需求状态

| 需求 | 状态 | 说明 |
|---|---|---|
| 64 位数值化 | ✅ | 槽是 8 字节，写入完整 64 位 |
| 与 32 位运算兼容 | ✅ | 游戏读同一槽，截断到 32 位 |
| 存档能存住 | ✅ | 就是游戏变量 |
| 语法与原版相同 | ✅ | 简写 + 完整两种都工作 |
| **log 完整输出 64 位** | ⚠️ | **`[?var]` 只能显示 32 位，需要分档方案** |

### 22.6 剩余工作

| 任务 | 说明 |
|---|---|
| **log 分档方案** | 参照原版 `temp_display_T/B/M`，把 64 位拆成多个 32 位变量供 log 显示 |
| `add_to_variable64` | 同类实现（同样用 hook + 标记） |
| effect 改名 | `var64_set_a` -> `set_variable64`（已做）、`var64_add_a` -> `add_to_variable64` |
| `var64_show_a` 是否需要 | 待定（`log` 已能读） |
| 实例释放 | 目前每次 malloc 544 字节未回收 |
| 数学表达式形式 | `{ 名字 = { value = X  multiply = 2 } }`，优先级最低 |
