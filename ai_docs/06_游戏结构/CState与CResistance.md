# CState 与 CResistance

> 全部结论来自 HOI4 1.19.3 的反汇编 + 运行时 RTTI/内存取证，非推测。
> 这些是引擎的通用结构知识，与具体 mod 无关。

## RTTI 取证方法（本 exe 特点）

MSVC x64 的虚表前面是 `COL`（Complete Object Locator）指针，且本 exe 里
`COL` 的 `pTypeDescriptor` 是 **4 字节 RVA**（不是 8 字节指针）：

    vtable_rva -> COL = *(vtable - 8)
    signature   = COL + 0x00 (u32, 应为 1)
    offset      = COL + 0x04 (u32)
    cdOffset    = COL + 0x08 (u32)
    pTypeDescriptor  = COL + 0x0C (u32, RVA!)
    pClassDescriptor = COL + 0x10 (u32, RVA)

    类名 = *(base + pTypeDescriptor + 0x10)   // TypeDescriptor: pVFTable(8) + spare(8) + name

读出来形如 `.?AVCState@@`。

## 已确认的虚表

| 类 | vtable RVA | 类名 |
|---|---|---|
| `CState` | `0x2936cc0` | `.?AVCState@@` |
| `CResistance` | `0x297e370` | `.?AVCResistance@@` |
| `CCountryOccupationStatus` | `0x2984978` | `.?AVCountryOccupationStatus@@` |

## CState 字段（实测）

| 偏移 | 内容 |
|---|---|
| +0x000 | vftable |
| +0x268 | **`CResistance` 子对象** |
| +0x630 | 数组数据指针 |
| +0x63C | 该数组长度 |

## CResistance 字段（实测）

| 偏移 | 内容 |
|---|---|
| +0x000 | vftable |
| **+0x050** | **`_OccupiedCountryTag`**（占领国 tag；**未占领时为 0**） |
| +0x118 | 某容器（`0x557840` 操作） |
| anon +0x058 | 某容器（`0x557840` 操作） |
| +0x210 | 数组数据指针 |
| +0x21C | 该数组长度 |
| **+0x208** | **byte 启用标志**（非 0 表示抵抗系统对该州启用） |

## 关键函数

| RVA | 语义 |
|---|---|
| `0x9cfb10` | 遍历所有 `CState` |
| `0x9e02c0` | `CState` 的每日更新（`this` = `CState`） |
| `0xf9b4b0` | 检查函数；`dl != 0` 时直接返回 `CResistance+0x208` |
| `0xf91850` | `CResistance` 的更新（`this` = `CResistance`）；开头 `cmp byte [rcx+0x208], 0 / je` 跳过 |
| **`0xf99d30`** | **`CResistance::GetOccupationLaw`** |
| `0xff3be0` | `GetOccupationData(tag)` — 按 tag 取占领数据，**无数据返回 NULL** |
| `0xff8290` | 有占领数据时取占领法（`GetOccupationLaw` 的尾调用目标） |

## GetOccupationLaw 的完整逻辑（0xf99d30）

    push rbx / sub rsp,0x30
    mov  rbx, rcx                  ; this = CResistance
    mov  rcx, [rcx + 8]
    add  rcx, 0xcc
    call 0xbb48f0                  ; 取 CCurrentGameState
    call 0x6cf810                  ; 取 map
    lea  rdx, [rbx + 0x50]         ; _OccupiedCountryTag
    call 0xff3be0                  ; GetOccupationData(tag)
    test rax, rax
    je   0xf99d73                  ; NULL -> 打日志
    ...
    jmp  0xff8290                  ; 有数据 -> 取占领法

日志分支（`0xf99d73`）里 `mov r8d, 0x261`，**0x261 = 609**，与日志的
`resistance.cpp:609` 精确对应 —— 这是确认函数身份最硬的证据。

## 调用链

    0x9cfb10   遍历所有 CState
      -> 0x9e02c0   CState 每日更新
           rsi = this (CState)
           res = this + 0x268            ; CResistance
           lea rcx, [res]; mov dl, 1
      -> 0xf9b4b0   检查(返回 byte)
      -> 0xf91850   CResistance::Update
           cmp byte [res + 0x208], 0
           je  跳过
      -> 0xf99d30   GetOccupationLaw
           tag = res + 0x50
      -> 0xff3be0   GetOccupationData(tag)

调用次数实测：hook `0x9e02c0` 得到 446 次（= 州总数），
hook `0xf9b4b0` 得到 `total=158681, 返回非 0 = 115842`。

## 可利用的判据

| 想判断 | 读什么 |
|---|---|
| 该州有没有抵抗系统在跑 | `CResistance+0x208 != 0` |
| 该州的占领国 | `CResistance+0x50`（tag；0 表示无） |
| 该州能否取到占领法 | `GetOccupationData(tag)` 是否返回 NULL（`0xff3be0`） |

## 取证工具

`test/probes_js/` 下几个通用探针：

| 文件 | 用途 |
|---|---|
| `_dis.js` | 用 Frida `Instruction.parse` 反汇编任意 RVA（无需 IDA）；正确用 `m.base` 算 RVA |
| `_rtti.js` | 由虚表 RVA 查类名（含本 exe 的 4 字节 RVA 特性） |
| `_hex.js` | 读写任意 RVA 的字节/字符串 |
| `_xref.js` | 在代码段扫 rip-relative 引用，定位引用了某字符串的指令 |
| `_fn.js` / `_outer.js` | hook 指定函数入口，打印 `this`、类名和调用栈 |
| `_logcallers.js` | 统计某个函数被哪些调用者调用（按调用点分组计数） |

## 踩过的坑

- **RVA 一定要用 `绝对地址 - 模块基址`**。本 exe 基址不是 `0x140000000`（ASLR），
  用 `- 0x140000000` 会得到完全错误的地址。
- `Instruction.parse` 必须从**指令边界**开始，否则报 `invalid instruction`。
- `idat.exe` 在装了缺依赖的插件（如 `Kam1n0.py` 缺 `cefpython3`）时启动会卡在极早期；
  但它不是唯一出路 —— 上面的 Frida 探针可以完全替代 IDA 做反汇编与 xref。
- Frida 的 `Interceptor` 在 `onEnter` 里用 `args[i]` 对应 `rcx/rdx/r8/r9`；
  尾调用（`jmp`）不会出现在 backtrace 里。
## CResistance 启用标志的完整机制（深挖第二轮）

### 相关函数

| RVA | 语义 |
|---|---|
| **`0xf9ae60`** | **`CResistance::UpdateOccupation()`** — 决定 tag 与启用标志 |
| **`0xf986b0`** | **`ComputeOccupiedTag()`** — 在列表里查找并算出占领国 tag |
| `0xf9b050` | 真正把 tag 和 `+0x208` 写下去 |
| `0xf9c4b0` | 附加检查（返回 byte） |
| `0xf9c800` / `0xf97890` | 后续处理 |

### UpdateOccupation 的反汇编骨架（0xf9ae60）

    f9ae6f:  cmp dword ptr [rcx + 0x50], 0      ; tag > 0 ?
    f9ae76:  jle 0xf9ae94                       ; tag<=0 -> 去计算
    f9ae87:  call 0xf9c4b0                      ; 已有 tag: 检查
    f9ae8e:  jne 0xf9b039

    f9ae94:  call 0xf986b0                      ; computed = ComputeOccupiedTag()
    f9aeac:  cmp dword ptr [rsp + 0x48], 0      ; computed > 0 ?
    f9aeb1:  jle 0xf9b039                       ; <=0 -> 什么都不做
    f9aeca:  call 0xf9c4b0
    f9aed1:  je  0xf9b039
    f9aee0:  call 0xf97890                      ; tag>0 时的附加处理
    f9aef8:  call 0xf9b050                      ; ← 设置 tag 与 +0x208
    f9af05:  cmp byte ptr [rdi + 0x208], 0      ; 用标志决定后续

### 写 +0x208 的那一小段（0xf9b448 附近）

    f9b448:  cmp dword ptr [rbp + 0x50], 0      ; tag > 0 ?
    f9b44c:  jg  0xf9b452
    f9b44e:  xor al, al                         ; tag<=0 -> al = 0
    f9b450:  jmp 0xf9b46e
    f9b452:  lea r8, [rbp + 0x50]
    f9b464:  call 0xf9c4b0
    f9b46b:  setne al
    f9b46e:  mov byte ptr [rbp + 0x208], al     ; ← 写标志

即 **标志 = (tag > 0) && 检查通过**。

### ComputeOccupiedTag 的逻辑（0xf986b0）

    f986d3:  rcx = [this + 8]; rcx += 0xc8
    f986f7:  call 0xbb48f0                      ; CCurrentGameState
    f986ff:  call 0x6ec3e0
    f98704:  key = [rax]                        ; 存到 [rbp+0x40]
    f98712:  cmp dword ptr [rax + 0x484], 0     ; 上限 <= 0 -> 失败
    f9871d:  r14 = [this + 8]
    f98742:  rcx = [r14 + 0xb0]                 ; ★ 列表数据指针
    f9874c:  eax = [rcx]                        ; 列表元素
    f9874e:  cmp ebx, eax                       ; 与 key 比较
    f98750:  je  0xf988fd                       ; ★ 命中 -> 返回有效 tag
    f98763:  cmp r12d, eax                      ; 或用转换后的值比较
    f98766:  je  0xf988fd
    f98772:  cmp edi, [r14 + 0xbc]              ; 列表长度在 [r14+0xbc]

**它在一个列表（`[this+8]` 的 `+0xb0`，长度 `+0xbc`）里查找，命中才返回有效 tag。**

### 运行时实测（spawn + hook，446 个州）

    hook 0xf9ae60 入口:  calls=446  tag0=446      所有州入口时 tag 都是 0
    hook 0xf9ae60 出口:  入口 tag=0/flag=0  ->  出口 tag=45/flag=1
    hook 0xf9b46e (写标志): total=446, tag 全部有效(45/33/57/44/...)
    出口记录 446 个地址, 稍后再读:  tag!=0 = 11   tag==0 = 435

**结论：初始化阶段 446 个州都被算出并写入 tag 且标志置 1；随后其中 435 个的 tag
变为 0，而标志没有跟着重算，于是后续每日更新在 tag=0 时调用 GetOccupationLaw 而报错。**

### 排查用探针

| 文件 | 用途 |
|---|---|
| `test/probes_js/_judge.js` | hook `0xf9ae60` 入口，统计 tag 分布 |
| `test/probes_js/_exit.js` | hook `0xf9ae60` 出口，对比入口/出口的 tag 与标志 |
| `test/probes_js/_wr.js` / `_wrbt.js` | hook `0xf9b46e` 写标志点，看 tag 与调用栈 |
| `test/probes_js/_poll.js` | 记录对象地址后周期读 tag，观察何时变 0 |
| `test/probes_js/_clr50.js` | 扫写 `[reg+0x50]` 的指令 |

### 方法论提示

- **hook 出口比 hook 入口更能说明状态变化**：入口 tag=0、出口 tag=45，一次就看出该函数自己会设置 tag。
- **判断「谁改了字段」**：先记录对象地址再周期读，比直接扫指令更快定位「何时变」；
  指令扫描对 `+disp32` 的多种编码（`89`/`88`/`c7`、SIB、REX 前缀）覆盖不全，容易漏。
- **`MemoryAccessMonitor` 是页级粒度**，且若目标在 hook 安装前就已改变，会完全抓不到；
  要与 hook 出口配合，在第一次出口时就装好。

### 时序实测（第三轮，决定性）

用 spawn 模式从进程创建起 hook，得到精确的调用与状态时间线：

    hook 0xf9b050 (SetTagAndFlag):
      calls=446  不同对象=446  被多次调用的=0  进入时 tag=0 的次数=446
    => 每个州只被设置一次, 进入时 tag=0, 出口时 tag 是有效值

    hook 0xf9ae60 期间周期检查已记录对象:
      第 20/40/.../446 次调用时, 其中 tag==0 的始终为 0
      446 次全部结束后:  recorded=446  tag0=435  tag!=0=11

    在 0xf9b050 第 446 次出口立刻装监控时读到:
      calls=446  res=446  tag0=435     <- 此刻前 435 个已经被清零

    SetTagAndFlag 逐次观察:
      37.0s  calls=446  不同对象=446  进入时tag=0=446
      40.0s  同上 (无重复调用)

游戏进地图约需 37~39 秒（spawn 起算），清零紧随其后、秒级内完成。

**结论：`UpdateOccupation` 对全部 446 个州都算出并写入了有效 tag、同时置启用标志；
随后 435 个州的 tag 被清零，而启用标志没有跟着重算。**

### 未解与已排除

- **未解**：清零那一步的具体代码尚未定位。
  `MemoryAccessMonitor` 在监控了 272/440 个页面的情况下仍抓不到对该字段的写入，
  说明它对这种高频短窗口场景不可靠；guard page + `Process.setExceptionHandler` 会干扰
  游戏自身的异常处理并导致进程退出，不可用。
- **已排除**（都做了对照实验）：
  - 覆盖 `common/occupation_laws`（整个目录禁用）—— 无效
  - 覆盖 `common/resistance_activity`（整个目录禁用）—— 无效
  - state 文件 owner / add_core_of 的 tag 合法性 —— 446 个文件全部合法
  - 移走重复的 bookmark 文件 —— 无效
  - 给 state 补 controller —— 无效（**注意：原版的 controller 必须写在日期块里**，
    形如 `1938.10.25 = { controller = JAP }`；裸写 `controller = X` 在 `history = {}` 里不生效，
    这也是那次实验无效的原因）

### 附加结构事实

- `CState + 0x0b0` = core tag 数组指针，`+0x0bc` = core 数量（实测 1 或 2）
- `CState + 0x0c8` / `+0x0cc` = 该州的 owner tag（等于 core 数组首元素）
- `CResistance + 0x008` = 指向所属 `CState` 的指针（反查很方便）
- `ComputeOccupiedTag` 就是拿 `CState+0xc8` 去 core 数组里找，**owner 必定在其中**，
  所以它对每个州都会返回有效 tag
