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