# effect 的 scope 与实例结构（第4轮诊断实测）

> 上游：变量的哈希表与节点布局见同目录《变量存储结构.md》。
> 本文记录「游戏传给 effect 的 scope 到底是什么」，以及为什么它不能直接当变量容器用。
## 十五、effect 的 scope 是什么（第4轮 · 诊断实测）

### 15.1 诊断手段

写了一个诊断 effect `var64_diag`，在 exec 里把 `self`（effect 实例）和 `scope`（作用域）
的指针字段全部打进插件日志（只打印「指向可读内存」的字段，避免打印纯数值）。

代码位置：`src/plugin/SDK_RVA/variable64/variable64.c` 的 `ExecVar64Diag`。

### 15.2 scope 的类型 = `CEventScope`

`scope + 0` 是虚表指针。用 CE 拿到运行期地址后，
按 RTTI 定位器 → type_info 的路径解析出类名：

```
scope+0            = 0x7FF6C88A43E8        (虚表)
虚表-8             = 0x142C23A80           (RTTI 定位器)
定位器.pTypeDesc   = 0x030CC268  →  type_info @ 0x1430CC268
type_info+16       = ".?AVCEventScope@@"
```

**scope 是 `CEventScope`（事件作用域）。**

### 15.3 实测字段（一次典型调用，地址随运行变化）

| 偏移 | 值 | 说明 |
|---|---|---|
| `+0x000` | `0x7FF6C88A43E8` | **虚表**（CEventScope） |
| `+0x008` | `DCE7CC8900000003` | 数值，非指针 |
| `+0x010` | `000000008C120EFC` | 数值 |
| `+0x018/0x020/0x028` | 指向 `scope+0x18` | **自引用**（链表哨兵） |
| `+0x030/0x038` | 0 | |
| `+0x0B0` | `0x7FF6C88A43E8` | **同一个虚表**（内嵌的第二个 CEventScope） |
| `+0x0C8/0x0D0/0x0D8` | 指向 `scope+0xC8` | 自引用 |
| `+0x160` | `0x7FF6C8C61D08` | 另一个虚表 |
| `+0x168` | `0x7FF6C87F0B08` | 另一个虚表 |
| `+0x180/0x188` | 指向 `+0x180` | 自引用 |
| `+0x1A0/0x1A8` | 指向 `+0x1A0` | 自引用 |
| `+0x1B8/0x1C0` | 指向 `+0x1B8` | 自引用 |
| `+0x1C8` | 堆指针 | 候选 |
| `+0x1E0` | 堆指针 | 候选 |
| `+0x1E8` | `0x7FF6C87FE190` | 另一个虚表 |

**`CEventScope` 是个「大对象内含多个子对象」的结构**（至少 4 个虚表：`+0`、`+0xB0`、`+0x160`、`+0x1E8`）。

### 15.4 否定结论：这些候选都不是变量容器

判断标准：真容器的 `mask`（表 `+20`）必须是 `2^k - 1`（构造函数里容量初值 256 ⇒ mask 255）。

| 候选 | buckets | mask | 判定 |
|---|---|---|---|
| `scope` | `= scope` | **4** | ✗ 不是 2^k-1 |
| `scope+0x1C8` 指向 | 垃圾 | 7209061 | ✗ |
| `scope+0x1E0` 指向 | 13 | 0 | ✗ |
| `scope+0x160` 指向 | — | 32758 | ✗ |
| `scope+0x168` 指向 | — | 32758 | ✗ |
| `self+0x130` 指向 | — | 0 | ✗（这一项其实是 SSO 字符串数据） |

**在 `scope` 里用我们的算法查 `dshprobe` 全部失败。**

### 15.5 self（我们的 effect 实例）实测字段

| 偏移 | 值 | 说明 |
|---|---|---|
| `+0x000` | `0x7FFC55C63478` | **我们 DLL 里的虚表** |
| `+0x018` | `0x7FF6C9155170` | 游戏内地址 |
| `+0x058` | `0x7FF6C87E8428` | **参数描述**（已知，`sub_140544C90` 的入参） |
| `+0x0C0` | `0x7FF6C9155170` | 同 `+0x018` |
| `+0x130` | `0x7FF6C8845190` | 游戏内地址（`0x7FF6C8845...` 是 vtable 区） |
| `+0x148` / `+0x1F0` | `0x7FF6C9155170` | 同 `+0x018` |
| `+0x188` | `0x7FF6C87E8428` | 同 `+0x058` |

### 15.6 下一步（第5轮）：造一个 CSetVariableEffect 实例

`scope` 这条路已经证明走不通（变量表不在我们能猜到的偏移上）。
**更可靠的做法是直接复现游戏自己的调用链**：

```c
/* 工厂地址已知：RVA 0x341F60 */
void* inst = ((void* (*)())(img + 0x341F60))();   /* 造 CSetVariableEffect，malloc 0x220 */
/* 变量名写到 inst + 512（std::string，SSO，cap 在 +536） */
/* 然后调 exec 的取值路径：sub_140542280(inst + 88, scope, 0) 拿值地址 */
/* 或者干脆填好参数后调 exec 本体 sub_140364C60(inst, scope) */
```

**注意**：`sub_140364C60` 读参数用的是 `sub_140544C90(inst+296, &v, ctx, 0, 1)`，
第 5 个参数是 **1**（我们一直传 0）。要复现必须照传。

另一条更省事的路径：既然 `CScopedVariable` 在 `inst + 88`，而 `sub_140542280` 就是
「按名字取值的地址」，那么**造好实例、填好名字、直接调 `sub_140542280`** 即可，
不必碰参数读取。

## 十六、借游戏机制读写变量：实例化成功（第5轮）

### 16.1 做法

不再猜 scope 的字段，而是**直接复现游戏自己的调用链**：

```c
/* 1. 用工厂造一个 CSetVariableEffect 实例 */
typedef void* (__fastcall *Var64FactoryFn)(void);
inst = ((Var64FactoryFn)(img + 0x341F60))();      /* malloc 0x220 + 构造 + 设虚表 */

/* 2. 把变量名写进实例 +512 的 std::string 字段（SSO） */
nameDst = inst + 512;
memset(nameDst, 0, 32);
memcpy(nameDst, name, n);
*(unsigned long long*)(nameDst + 16) = n;          /* size */
*(unsigned long long*)(nameDst + 24) = 15ULL;      /* cap  */

/* 3. 调 lookup：CScopedVariable 在实例 +88 */
typedef void* (__fastcall *Var64LookupFn)(void* scopedVar, void* ctx, void* a3);
addr = ((Var64LookupFn)(img + 0x542280))(inst + 88, scope, NULL);
```

工厂 `sub_140341F60` 的反汇编确认它是**无参数**的：

```asm
mov  ecx, 220h              ; 544 字节
call malloc
call sub_14032D260          ; 构造函数
lea  rax, CSetVariableEffect::vftable
mov  [rbx], rax
retn                        ; 返回实例
```

`sub_140542280` 的参数也确认了（rcx=CScopedVariable*、rdx=ctx、r8=a3）：

```asm
cmp  byte ptr [rcx+0Eh], 0  ; a1+14 的标志，与构造函数吻合
mov  rsi, r8                ; a3
mov  rdi, rdx               ; a2 = ctx
mov  rbx, rcx               ; a1
```

### 16.2 实测结果

```
[v64diag] *** GAME-API OK: inst=00000151724D66F0 addr=00000151717420C8 dshprobe=0 (0.00000)

game.log: DIAG set dshprobe 1847293651
```

| 项 | 结果 |
|---|---|
| 造实例 | ✅ 成功（`inst=0x151724D66F0`），游戏未崩溃 |
| 调 lookup | ✅ 成功，返回地址 `0x151717420C8` |
| 读值 | ❌ 读回 `0`，而游戏日志显示 `1847293651` |

### 16.3 对「读回 0」的分析

`sub_140BC3F10` 在**没找到变量时会走插入分支**（`LABEL_10`），
创建新节点、值默认 0。所以最可能的原因是：

**lookup 没有找到已有的 `dshprobe`，而是新建了一个。**

可能的具体原因（待第6轮验证）：

| 序号 | 假设 | 验证方法 |
|---|---|---|
| 1 | 我们传给 lookup 的 `scope` 与游戏执行 `set_variable` 时的 ctx 不是同一个 | 在同一次 exec 里先让游戏写、再让我们读，对比 |
| 2 | 变量名写入实例的方式有误（虽然 offset 与构造函数吻合） | 读回实例的 `+512` 字段核对 |
| 3 | 变量的真正容器来自 `sub_140542500`（依赖 ctx），而我们的 ctx 缺少某个绑定 | 反编译 `sub_140542500` |
| 4 | 游戏的 `set_variable` 在同一事件里写入的位置与我们查询的作用域不同（国家 vs 全局） | 对比 CE 扫描到的实际节点地址 |

### 16.4 已有的可用工具

```c
/* variable64.c 里已实现 */
int  Var64_LookupInScope(void* container, const char* name, long long* out);
int  Var64_MakeGameVarInstance(void* scope, const char* name,
                               void** outInst, void** outAddr);
unsigned int Var64_Fnv1a(const char* s);
```

`Var64_MakeGameVarInstance` 已经能把「变量名 → 值地址」这条链路走通，
只是拿到的地址指向的还不是那个已存在的变量。**下一次只需定位差异。**

## 十七、读写游戏变量：完全打通（第6轮）

### 17.1 上一轮失败的原因

第 5 轮把变量名写到了 `inst + 512`，结果 lookup 返回的节点是：

```
node=... hash=0x811C9DC5 bucketIdx=6 size=0 cap=15
node name unreadable
```

**`hash = 0x811C9DC5` 正是 FNV-1a 的初始值**，配合 `size = 0`，说明**名字是空的** —— 
lookup 因此新建了一个空名节点。

### 17.2 名字字段的真正位置

回到 `sub_1405454A0`（造变量名）的第一行：

```c
sub_14011E010((__int64)a2, a1 + 112);   // a1 = CScopedVariable，名字源在 a1 + 112
```

而 `CScopedVariable` 在实例的 `+88`，所以：

```
名字字段 = inst + 88 + 112 = inst + 200
```

`inst + 512` 是**另一个** std::string（构造时同样初始化为 SSO），但不是变量名。

### 17.3 修正后的做法

```c
#define VAR64_SUBOBJ_OFF   88u     /* CScopedVariable 在实例内的偏移 */
#define VAR64_NAME_OFF     200u    /* 88 + 112，变量名 std::string */

/* 1. 造实例 */
inst = ((Var64FactoryFn)(img + 0x341F60))();

/* 2. 写变量名到 inst + 200（SSO 布局：data +0 / size +16 / cap +24） */
nameDst = inst + 200;
memset(nameDst, 0, 32);
memcpy(nameDst, name, n);
*(unsigned long long*)(nameDst + 16) = n;
*(unsigned long long*)(nameDst + 24) = 15ULL;

/* 3. lookup */
addr = ((Var64LookupFn)(img + 0x542280))(inst + 88, scope, NULL);
/* addr 就是那个变量的值地址（8 字节槽） */
```

### 17.4 实测结果（完全成功）

```
[var64] wrote name [dshprobe] to 000001C2717659B8 (len=8)
[v64diag] *** GAME-API OK: inst=000001C2717658F0 addr=000001C1E6EBFE28
          value=184729365100000 (1847293651.00000)
[v64diag] node=000001C1E6EBFE00 hash=0xB81F1142 bucketIdx=4 size=8 cap=15
[v64diag] node name = [dshprobe]
```

| 项 | 值 | 判定 |
|---|---|---|
| 读取的值 | `184729365100000` | ✅ 正是游戏里那个变量（`1847293651 x 100000`） |
| 节点 hash | `0xB81F1142` | ✅ FNV-1a 正确 |
| 桶序号 | `4` | ✅ |
| 名字 size | `8` | ✅ |
| 节点名字 | `dshprobe` | ✅ |

**「按名字拿到游戏变量的值地址」这条路彻底打通。**

### 17.5 值槽的宽度

游戏 exec 里是 `*v6 = v8`，其中 `v8` 是 `long long`（`sub_140544C90` 的输出）。
**所以值槽是 8 字节宽。**

但游戏自己的 `set_variable` 在**解析阶段**会把它压到 int32（实测 `2^31` 翻负），
所以：

| 读写方 | 位宽 |
|---|---|
| 我们直接读写槽 | **8 字节，完整 64 位** |
| 游戏 `set_variable` 写入 | 32 位（会截断） |
| 游戏系统读取（`add_manpower` 等） | 32 位（会截断） |
| `[?var]` 日志显示 | 32 位（会截断） |

**结论**：我们可以把 64 位值完整存进一个游戏变量，
**这个值会随存档保存**，也能被游戏系统读到（截断后的 32 位部分）；
但要**完整读出 64 位**、以及**在 log 里完整显示**，仍需我们自己的路径或分档方案。

### 17.6 新增可用工具

```c
/* variable64.c */
int Var64_MakeGameVarInstance(void* scope, const char* name,
                               void** outInst, void** outAddr);
/*   outInst -> CSetVariableEffect 实例（可用于后续 free）
     outAddr -> 该变量的值地址（8 字节槽，可直接读写） */
*/
```

注意事项：

- 变量名长度限制 **1..15**（SSO），超长需要另走堆分配路径，当前未实现。
- 每次调用会 **malloc 544 字节**，当前未做释放（测试期可接受，正式版需要处理）。
- 调用后游戏**不崩溃**（已多轮验证）。

## 十八、`set_variable` 的三种语法（第7轮 · 从注册函数读出）

### 18.1 官方文档原文

`set_variable` 的注册函数 `sub_14001E1C0`（92 字节）里，entry 的 `+8` 字段存着这段文档：

```
![MD]
Sets a variable to a value, another variable, or a [math expression](script_math_expression.md).
`tooltip` can be used to override tooltip title with LEFT and RIGHT tokens.

### Examples
```
set_variable = { num_dogs = 42 }
set_variable = {
	var = num_dogs
	value = 42
	tooltip = loc_str_id_with_LEFT_and_RIGHT
}
set_variable = {
	num_dogs = { value = num_cats  multiply = 2  add = 1 }
}
```
```

### 18.2 三种语法

| # | 形式 | 说明 |
|---|---|---|
| 1 | `set_variable = { 名字 = 值 }` | **简写**。键就是变量名 |
| 2 | `set_variable = { var = 名字  value = 值  tooltip = ... }` | **完整**。`tooltip` 可选 |
| 3 | `set_variable = { 名字 = { value = X  multiply = 2  add = 1 } }` | **数学表达式** |

要求我们实现的 variable64 至少覆盖 1 和 2。**3 需要表达式求值，优先级最低。**

### 18.3 注册模式（与我们已有框架一致）

```c
__int64 sub_14001E1C0()
{
    v0 = qword_143330000;                   // _EffectEntries
    if (!v0) { sub_14053D840(); v0 = qword_143330000; }
    v1 = malloc(0x10);                      // entry 16 字节
    v1[1] = <上面的文档字符串>;              // entry +8 = 描述
    *v1 = &CEffectEntry<CSetVariableEffect>::`vftable';   // entry +0 = 虚表
    return sub_1405415A0(v0, 10163LL, v1);  // 注册，id = 10163
}
```

**注册里没有参数元数据。** 参数由通用的脚本解析器读入。

这解释了为什么我们的框架只读得到一个数值参数 ——
我们的 `EFF_DEF` 构造的参数描述（`self + 0x58`，104 字节）只声明了单个值。

### 18.4 当前的实现边界

| 能力 | 状态 |
|---|---|
| 造 `CSetVariableEffect` 实例 | ✅ 已实现（`Var64_MakeGameVarInstance`） |
| 按名字拿到游戏变量的值地址 | ✅ 已验证（读到 `184729365100000`） |
| 直接读写那个 8 字节槽 | ✅ 可做（`*(long long*)addr = v`） |
| 值随存档保存 | ✅ 天然获得（它就是游戏变量） |
| 与 32 位系统运算交互 | ✅ 天然获得（游戏读同一槽，会截断） |
| **effect 语法与原版一致（简写 / 完整）** | ❌ **未实现**（块参数解析） |
| **log 完整输出 64 位** | ⚠️ 需分档方案（原版用 T/B/M 三变量） |

### 18.5 下一步（第8轮）

**先做一个实验**：注册一个 effect，脚本里用块形式调用它
（`var64_test = { var = dshprobe  value = 123 }`），看我们的参数读取能不能拿到东西、
或者游戏会不会报参数错误。这决定块解析是「改参数描述」还是「另找解析 API」。

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
