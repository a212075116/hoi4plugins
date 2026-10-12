# CString 布局与 SSO 上限

> 源码：src/plugin/SDK_RVA/console/console_cmd.h 的 CmdString

## 布局

MSVC std::string = **32 字节**：

| 偏移 | 大小 | 含义 |
|---|---|---|
| +0x00 | 16 | union { char buf[16]; char* ptr; } |
| +0x10 | 8 | size |
| +0x18 | 8 | capacity |

**capacity <= 15 时走 SSO**：内容直接放在 +0x00 的 16 字节里
（此时那 16 字节既是 buf 也是 ptr 的存储位置）。
capacity > 15 时 +0x00 存堆指针。

## SSO 上限 15

缓冲 16 字节**含结尾 NUL**，所以正文最多 **15 字符**。

**这是本工程踩得最痛的一个坑，前后崩了三次游戏：**

| # | 位置 | 症状 |
|---|---|---|
| 1 | CmdString 定义写成 {char*; size_t; size_t} = 24 字节 | sizeof(ConsoleCommand)=352 而非 456，整个表项布局错位 |
| 2 | 描述串 56 字符按 SSO 往 16 字节缓冲 memcpy | 冲垮紧邻的 +0x68 handler 函数指针，游戏当场崩 |
| 3 | SetMsg 放行到 127 字符 | 只敲命令名回车（无参分支消息 43 字符）时又崩一次 |

## 修正

- ConsoleCmd_WriteString / ConsoleCmd_WriteShortString：硬截断到 15 字符
- 编译期断言，让尺寸错误在**编译期**暴露：

      typedef char assert_cmdstring[(sizeof(CmdString) == 32) ? 1 : -1];
      typedef char assert_cmdentry [(sizeof(CmdEntry)  == 456) ? 1 : -1];

- 注册器运行时自检，超长就**跳过该条并打日志**，而不是冒险写入

自检实战拦截（真实发生）：

    [cmdreg] skip setcamheight: usage len 16 > SSO max 15
    [cmdreg] nothing passed checks, abort

"setcamheight <h>" 恰好 16 字符，被拦住了，**这次没崩**。

## 长字符串怎么办

名字/描述/用法受 15 字符限制，但**回显消息可以任意长**。
做法是调用游戏的 sub_140129CA0，它等价于 std::string::assign：

    void** sub_140129CA0(void** Dst, void* Src, size_t Size)
    {
        n0xF = Dst[3];                  // 旧 capacity
        if (Size > n0xF) {
            v8 = max(Size | 0xF, n0xF/2 + n0xF);
            v11 = j_j__malloc_base(v8 + 1);
            Dst[2] = Size;              // size
            Dst[3] = v8;                // cap
            memcpy(v11, Src, Size);
            if (n0xF <= 0xF) { *Dst = v11; return Dst; }   // SSO 转堆
            j_free(*Dst); *Dst = v11;                      // 堆换堆
        }
    }

**前置条件**：Dst 必须是合法空串（cap=15, size=0, buf[0]=0），
否则 assign 会按垃圾 cap 去 free 野指针。这就是 ConsoleCmd_InitResult 的作用。
