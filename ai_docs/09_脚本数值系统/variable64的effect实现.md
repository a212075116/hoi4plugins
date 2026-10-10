# variable64 的 effect 实现（第11~12轮）

> 上游：需求与验证历程见《variable64实现与验证.md》。
> 本文记录 `set_variable64` / `add_to_variable64` / `log_variable64` 的实现与实测。
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

## 二十三、三个 effect 全部实现（第12轮）

### 23.1 设计：一个 hook，三个 effect

hook 里用**实例标记**区分调用者，标记值不同则走不同分支：

```c
#define VAR64_MARK_SET     0x53343656u   /* "V64S" */
#define VAR64_MARK_ADD     0x53343641u   /* "V64A" */
#define VAR64_MARK_LOG     0x5334364Cu   /* "V64L" */

static long long __fastcall Var64_GameSyntaxDetour(void* self, void* ctx)
{
    unsigned int mark = 0;
    if (self && ConsoleCmd_IsReadable((char*)self + 505, 7))
        mark = *(unsigned int*)((char*)self + 505);
    if (mark == VAR64_MARK_SET) return Var64_DoSetVariable64(self, ctx);
    if (mark == VAR64_MARK_ADD) return Var64_DoAddToVariable64(self, ctx);
    if (mark == VAR64_MARK_LOG) return Var64_DoLogVariable64(self, ctx);
    return g_var64OrigGameSetExec(self, ctx);   /* 原版 set_variable 放行 */
}
```

每个 effect 有自己的 factory，工厂里写对应标记：

```c
static void* __fastcall Var64_SetVariable64Factory(void) { return Var64_MarkedFactory(VAR64_MARK_SET); }
static void* __fastcall Var64_AddToVariable64Factory(void) { return Var64_MarkedFactory(VAR64_MARK_ADD); }
static void* __fastcall Var64_LogVariable64Factory(void) { return Var64_MarkedFactory(VAR64_MARK_LOG); }
```

### 23.2 公共的解析函数

```c
static int Var64_ResolveGameVariable(void* self, void* ctx, long long* outValue,
                                     unsigned char** outAddr, char* nameBuf,
                                     unsigned int nameBufSize);
```

一次做完三件事：

1. **读变量名** —— `self + 200` 的 std::string（SSO：data `+200` / size `+216` / cap `+224`）
2. **读参数值** —— `sub_140544C90(self + 296, &v, ctx, 0, 1)`（**第 5 参数传 1**）
3. **拿值地址** —— `sub_140542280(self + 88, ctx, NULL)`

### 23.3 三个 effect

| effect | 名字 | tokenId | 行为 |
|---|---|---|---|
| `gamesetvar64` | `set_variable64` | 20163 | `*(long long*)addr = 值` |
| `gameaddvar64` | `add_to_variable64` | 20164 | `*(long long*)addr += 值` |
| `gamelogvar64` | `log_variable64` | 20165 | 读值并以完整精度写日志 |

三者都用**完全相同的 entry/factory 配置**（游戏 entry 虚表 + 游戏实例 + 我们的标记），
所以**语法与 `set_variable` 完全一致**。

### 23.4 实测（一次事件跑完五项操作）

脚本：

```
set_variable64 = { var = v64c value = 12345678901234 }
log_variable64 = { var = v64c }
add_to_variable64 = { var = v64c value = 1000000000000 }
log_variable64 = { var = v64c }
add_to_variable64 = { v64c = -2000000000000 }
log_variable64 = { v64c = 0 }
log = "V64C vanilla log = [?v64c]"
```

插件日志：

```
[var64] set_variable64 v64c = 12345678901234 (raw 1234567890123400000)
[var64] log_variable64 v64c = 12345678901234 (raw 1234567890123400000)
[var64] add_to_variable64 v64c: 12345678901234 + 1000000000000 = 13345678901234
[var64] log_variable64 v64c = 13345678901234 (raw 1334567890123400000)
[var64] add_to_variable64 v64c: 13345678901234 + -2000000000000 = 11345678901234
[var64] log_variable64 v64c = 11345678901234 (raw 1134567890123400000)
```

**全部精确到个位**（数值远超 int32 上限），负数运算也正确。

### 23.5 原版 log 的对照

同一个事件里的原版语句：

```
log = "V64C vanilla log = [?v64c]"
```

游戏日志输出：

```
[23:13:27][0500.01.01.01][effectbase.cpp:1783]: V64C vanilla log = -1624694798
```

**原版 `[?var]` 只能给出 32 位（截断成有符号），而 `log_variable64` 给出完整的 `11345678901234`。**

这就是「让 log 能输出 64 位」的落地方式：**新增一个 effect，而不是改原版 log 的格式化**
（原版的格式化输入就是 int32，改不了）。

### 23.6 需求完成状态

| 需求 | 状态 | 证据 |
|---|---|---|
| 64 位数值化 | ✅ | 槽是 8 字节，写入 `1234567890123400000` 无损 |
| 与 32 位运算兼容 | ✅ | 游戏读同一槽（截断到 32 位） |
| 语法与原版相同 | ✅ | 简写 + 完整两种都工作 |
| log 能输出 64 位 | ✅ | `log_variable64` 输出完整值 |
| **存档能存住** | ⚠️ | 变量就是游戏变量，理论随存档；**但尚未做读档实测** |

### 23.7 剩余工作

| 任务 | 优先级 |
|---|---|
| **存档读档实测**（写入 -> 存档 -> 读档 -> 校验） | **高** |
| 实例释放（当前每次调用 malloc 544 字节未回收） | 中 |
| 旧 effect 清理（`var64_set_a` / `var64_add_a` / `var64_show_a` 已被取代） | 中 |
| 数学表达式形式 `{ 名字 = { value = X  multiply = 2 } }` | 低 |
