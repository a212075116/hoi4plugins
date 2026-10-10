# variable64 的存档验证（第13~14轮）

> 上游：effect 实现见《variable64的effect实现.md》。
> 本文记录存读档工具链、32 位序列化限制的发现，以及高低位拆分方案及其验证。

## 一、存读档工具链

| 项 | 值 | 来源 |
|---|---|---|
| 存档命令 | **`savegame <名字>`** | 字符串 `0x142729728`，描述 `0x142729740` "Creates a save file." |
| 自动存读档测试 | `savecheck` | `0x142729768`，描述 `0x142729780` |
| 强制文本存档 | 启动参数 **`-force_text_save`** | `0x142717028` |
| 存档目录 | `Documents/Paradox Interactive/Hearts of Iron IV/save games/` | 实测 |
| 二进制存档头 | `HOI4bin5` | 实测 |
| 文本存档头 | **`HOI4txt`** | 实测 |

调用脚本（本轮新增）：

```
python hoi4plugins/test/modules/console/numtest_run_command.py savegame zz_v64_save
```

## 二、发现：游戏变量序列化是 32 位

### 2.1 现象

写入 `set_variable64 = { var = v64save value = 80000000000000 }`（raw `8000000000000000000`），
文本存档（`zz_v64_split.hoi4`）里是：

```
185000: v64save=19391.44704
```

验算：`80000000000000 mod 2^32 = 1939144704`，且 `19391.44704 x 100000 = 1939144704`。

**⇒ 存档存的是 `value mod 2^32`（value = raw / 100000）。**

与 `[?var]` 的 log 行为一致 —— **两处都是 32 位**。

### 2.2 顺带确认：定点上限

测试 `99999999999999` 时读到 `-84467440737096`：

```
9999999999999900000 - 2^64 = -8446744073709651616   （回绕，完全吻合）
```

**定点上限 = `2^63 / 100000 = 92233720368547`（约 9.22e13）**，超出会回绕。

## 三、解决方案：高低 32 位拆分

### 3.1 设计

```c
#define VAR64_HIGH_SUFFIX  "_hi"
#define VAR64_NAME_LIMIT   15u    /* SSO 上限 */

/* 写入：把 value 拆成两个 32 位，各占一个游戏变量 */
long long value = rawValue / 100000;
unsigned long long uv = (unsigned long long)value;
lo = (unsigned)(uv & 0xFFFFFFFF);
hi = (unsigned)((uv >> 32) & 0xFFFFFFFF);
写 lo 到主变量（游戏序列化时会存它的低 32 位，正好是 lo）
写 hi 到 <名字>_hi

/* 读取：从两个变量重组 */
value = ((unsigned long long)hi << 32) | lo;
raw   = value * 100000;
```

**关键点：拆分的基准必须是 `value`（= `raw / 100000`）而不是 `raw`**，
因为游戏的序列化先做定点还原再取低 32 位。

### 3.2 新增函数

```c
static int  Var64_MakeHighPartName(const char* name, char* out, unsigned int outSize);
static unsigned char* Var64_ResolveAddressByName(void* self, void* ctx, const char* name);
static void Var64_StoreSplit64(void* self, void* ctx, const char* name,
                               unsigned char* lowAddr, long long rawValue);
static long long Var64_LoadSplit64(void* self, void* ctx, const char* name,
                                   unsigned char* lowAddr, unsigned int* outLo,
                                   unsigned int* outHi);
```

三个 effect 都改用拆分逻辑。

## 四、验证

### 4.1 运行期日志

```
[var64] split v64save: value=80000000000000 lo=1939144704 hi=18626
[var64] set_variable64 v64save = 80000000000000
[var64] log_variable64 v64save = 80000000000000 (lo=1939144704 hi=18626)
```

### 4.2 文本存档（`zz_v64_split.hoi4`，头 `HOI4txt`）

```
185000: v64save=19391.44704
185001: v64save_hi=0.18626
```

`19391.44704 x 100000 = 1939144704`（lo），`0.18626 x 100000 = 18626`（hi）。

### 4.3 二进制存档（`Test_02.hoi4`，头 `HOI4bin5`）

字节级解析：

```
v64save     名字在 2237514
  后跟      00 0d 00 00 00 | 00 00 95 73 00 00 00 00
  值        = 0x73950000 = 1939144704      <-- lo

v64save_hi  名字在 2237537
  后跟      00 0d 00 | c2 48 00 00 00 00 00 00
  值        = 0x48C2 = 18626                <-- hi
```

### 4.4 重组验证

```python
lo = 1939144704; hi = 18626
value = (hi << 32) | lo        # = 80000000000000   MATCH
raw   = value * 100000         # = 8000000000000000000  MATCH
```

## 五、未完成的验证：真实读档恢复

### 5.1 尝试

用启动参数 `-continuelastsave` 启动（字符串 `0x142717440` 处发现），期望自动读最近的存档。

### 5.2 结果：没有生效

`game.log`：

```
[23:25:46][no_game_date][gamestate.cpp:2844]: Loaded 9975 provinces.
[23:26:07][no_game_date][gameapplication.cpp:2968]: Resetting game
[23:26:08][0500.01.01.01][history.cpp:165]: Executing History from -1.1.1.1 to  2.1.1.1
[23:26:10][0500.01.01.01][frontend.cpp:682]: [[ Launching SINGLEPLAYER-game ]]
```

出现 `Resetting game` 和 `Launching SINGLEPLAYER-game` —— **开的是新游戏，不是读档**。

读档后触发 `log_variable64`：

```
[var64] log_variable64 v64save = 0 (lo=0 hi=0)
```

### 5.3 中间环节的旁证

`savecheck`（存 Test_01 -> 读档 -> 存 Test_02）执行成功（`out->ok = 1`），
而且 `Test_02.hoi4` 里**两个变量名和值都在**（见 4.3）。

**说明存档侧的往返是好的**（读档后重新序列化，值仍然正确），
只是「启动到读档」这一步没有走通。

### 5.4 尚未尝试的读档途径

| 途径 | 说明 |
|---|---|
| 主菜单「继续游戏」 | 需要 GUI 操作（用户手动） |
| 找真正的读档启动开关 | `-continuelastsave` 无效，可能有别的名字 |
| 从主菜单调用读档 | 需要定位对应的按钮处理函数 |

## 六、需求状态

| 需求 | 状态 | 证据 |
|---|---|---|
| 64 位数值化 | ✅ | 插件内 8 字节槽读写完整 64 位 |
| 与 32 位运算兼容 | ✅ | 游戏读同一槽（截断到 32 位） |
| **存档中能存住** | ✅ | **文本/二进制存档里两个分量都正确** |
| 语法与原版相同 | ✅ | 简写 + 完整两种都工作 |
| log 能输出 64 位 | ✅ | `log_variable64` 输出完整值 |
| 读档后完整恢复 | ⚠️ | 未验证（读档途径没走通） |

## 七、已知限制

| 限制 | 说明 |
|---|---|
| 有效数值上限 | `9.22e13`（定点 `2^63/100000`），超出回绕 |
| 变量名长度 | 1..15（SSO），且加上 `_hi` 后仍须 <= 15 |
| 每个变量占两个槽 | 主变量 + `_hi` |
| 实例未释放 | 每次 effect 调用 malloc 544 字节，当前不回收 |
| 与游戏的 32 位运算 | 游戏只看到低 32 位（高位在 `_hi` 里） |

## 八、读档途径的进一步探索（第15轮）

### 8.1 启动参数表

在 `0x142716c00` ~ `0x142717600` 区段 dump 出完整的启动参数名，与存档相关的有：

| 参数 | 地址 | 说明 |
|---|---|---|
| `force_text_save` | `0x142717028` | **有效**（让存档变成文本格式） |
| `allowoldsave` / `allowoldsaves` | `0x142717048` / `0x142717058` | 允许旧存档 |
| `start_save` | `0x142717068` | 试过，**无效** |
| `continuelastsave` | `0x142717440` | 试过，**无效** |
| `autosave` / `autosave_count=` | `0x142716d88` 附近 | 自动存档 |
| `scenario_testing.run_fixture save_load_exit.txt` | `0x142716e00` | 官方存读档测试夹具 |
| `scenario_test` / `scenario_testing.run_all_tests` | — | 场景测试框架 |

两个存档参数都只有 1 处引用，落在巨大的命令行解析函数里：

| 参数 | 引用点 | 所在函数 | 函数大小 |
|---|---|---|---|
| `start_save` | `0x140126c53` | `sub_140125090` | 7359 字节 |
| `continuelastsave` | `0x140127d04` | `sub_140126E50` | 7282 字节 |

### 8.2 实测：两个参数都无效

**`-start_save=zz_v64_split`**：

```
game.log: [23:29:47][no_game_date][gameapplication.cpp:2968]: Resetting game
          [[ Launching SINGLEPLAYER-game ]]
读档后 log_variable64 v64save = 0 (lo=0 hi=0)
```

**`-continuelastsave`**（第 14 轮）：同样开的是新游戏。

⇒ 两者都先进 `Resetting game` + `Launching SINGLEPLAYER-game`，即**新游戏流程**。

### 8.3 `savecheck` 不可用于正常游戏

第 14 轮执行 `savecheck` 成功（生成 `Test_01` / `Test_02`），但第 15 轮再执行时
**游戏直接崩溃**。

⇒ 它是**自动化测试框架**的一部分，需要特定的测试环境（对应 `scenario_testing` 系列参数）。

### 8.4 `settings.txt` 的存档格式开关

```
debug_saves=0
autosave="MONTHLY"
autosave_tocloud=no
save_career_to_cloud=yes
save_as_binary=yes        <-- 存档格式开关
```

`-force_text_save` 就是覆盖这个开关的。

### 8.5 尚未走通的读档途径

| 途径 | 状态 |
|---|---|
| `-continuelastsave` | 无效 |
| `-start_save=<名字>` | 无效 |
| `savecheck` | 会崩溃，不可用 |
| 主菜单「继续游戏」 | 需要 GUI 操作（游戏忽略合成输入，无法脚本化） |
| 找读档函数直接调用 | 只找到错误报告函数 `sub_142590AE0` / `sub_142590C40` / `sub_140C3B840`，不是入口 |

**下一步可选**：

1. 请用户在游戏里手动读档一次，然后触发 `zzdatetest.46` 校验（最可靠）
2. 继续追主菜单「继续」按钮的处理函数，用 CE 直接调用

## 九、旧 effect 清理（第15轮）

`set_variable64` / `add_to_variable64` / `log_variable64` 三个 effect 已经完全取代了
早期的槽位版，因此移除注册：

| 移除的 effect | 原因 |
|---|---|
| `var64_set_a` | 被 `set_variable64` 取代 |
| `var64_add_a` | 被 `add_to_variable64` 取代 |
| `var64_show_a` | 被 `log_variable64` 取代 |
| `var64_diag` | 诊断用途已完成 |

现在 `g_var64EffectDefs[]` 只含三个正式 effect。

## 十、控制台命令表全枚举（第16轮）

### 10.1 命令表结构

从 `test/modules/console/command_check.js` 得到（已在项目中）：

```javascript
const MGR_RVA = 0x35E1A80;   /* 命令管理器全局 */
const ENTRY   = 456;         /* 每条命令的字节数 */

mgr     = *(hoi4.exe + 0x35E1A80)
data    = *(mgr + 0)         /* 命令数组 */
cap     = *(mgr + 8)
count   = *(mgr + 12)

/* 每条命令（entry 基址 + 偏移） */
entry + 0x00  int          flag
entry + 0x08  CString32    name
entry + 0x28  CString32    usage
entry + 0x48  CString32    desc
entry + 0x68  ptr          handler
entry + 0x80  int          argCount
```

CString32 布局：`{union{char[16]; char*}, size_t size, size_t cap}`（cap <= 15 时数据内联）。

### 10.2 实测枚举结果

CE 读取（`count = 386`），筛出含 `save` / `load` / `continue` 的：

```
mgr=2627623B240 data=26276DAEF00 cap=474 count=386
[11]  map_icon_reload_type  argc=1
[74]  reloadinterface       argc=0
[75]  reloadtechnologies    argc=0
[78]  reloadoob             argc=1
[81]  reloadfx              argc=1
[117] savegame              argc=0
[118] savecheck             argc=0
[154] cityreload            argc=0
[164] reload_textures       argc=1
[176] reloadweather         argc=1
[185] gbreload              argc=0
[256] test_save_mode        argc=0
[374] reload                argc=1
matched=13
```

### 10.3 ★ 结论：控制台没有读档命令

**整张表里没有任何「载入存档」命令。** 与存档相关的只有 `savegame`（存）和 `savecheck`
（自动化测试，正常游戏会崩）。

⇒ **读档只能从 GUI 主菜单走**，而游戏忽略合成输入 ⇒ **无法脚本化**。

### 10.4 由此得到的判断

| 环节 | 状态 | 证据 |
|---|---|---|
| 写入 64 位到槽 | ✅ | 插件日志 `split ... lo=... hi=...` |
| 存档序列化 | ✅ | 文本存档 `v64save` / `v64save_hi` 都是正确的值 |
| 二进制存档 | ✅ | 字节级解析出 `0x73950000`（lo）和 `0x48C2`（hi） |
| 重组数学 | ✅ | `(hi << 32) \| lo` = 原值，Python 验算 MATCH |
| 读档恢复 | ⏳ | **没有自动化手段**；需要 GUI 手动读档 |

**「读档后写回槽」这一步由游戏自己完成**（它对 `_hi` 变量做与主变量完全一样的处理），
所以存档内容的正确性是目前能拿到的最强证据。
