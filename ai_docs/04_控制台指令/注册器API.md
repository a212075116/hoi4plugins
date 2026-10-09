# 注册器 API

> 源码：src/plugin/console_cmd.h / console_cmd.c

## 目的

把"往游戏里加一条控制台指令"收敛成**填一个结构体 + 调一次注册**。

## 用法

    static long long __fastcall OnMyCmd(CmdResult* out, CmdArgs* args)
    {
        char a[64];
        ConsoleCmd_InitResult(out);
        if (ConsoleCmd_GetArg(args, 0, a, sizeof(a)))
            ConsoleCmd_SetMessage(out, "got an argument");
        else
            ConsoleCmd_SetMessage(out, "no argument");
        out->ok = 1;
        return (long long)out;
    }

    static const CmdDef kCmds[] = {
        { "mycmd", "My command", "<arg>", 1, { "<arg>" }, &OnMyCmd },
    };

    ConsoleCmd_RegisterAll(kCmds, 1);

## API

| 函数 | 作用 |
|---|---|
| int ConsoleCmd_RegisterAll(const CmdDef* defs, int n) | 注册一批（上限 CMD_MAX_BATCH=16）；返回成功条数 |
| void ConsoleCmd_InitResult(CmdResult* out) | 把 message 置为合法空串（**必须先调**） |
| void ConsoleCmd_SetMessage(CmdResult* out, const char* s) | 写消息，任意长度 |
| int ConsoleCmd_GetArg(CmdArgs* args, int i, char* dst, size_t n) | 取第 i 个参数 |
| int ConsoleCmd_IsReadable(const void* p, size_t n) | 内存可读性检查 |

## CmdDef

    typedef struct {
        const char*  name;          // <= 15 字符
        const char*  description;   // <= 15 字符
        const char*  usage;         // <= 15 字符, 可为 NULL
        int          argCount;      // 0..CMD_MAX_ARGS(8)
        const char*  argNames[CMD_MAX_ARGS];   // 每个 <= 15 字符, 可为 NULL
        CmdHandlerFn handler;
    } CmdDef;

## SetMessage 的两条路径

    n <= 15  -> 就地写 SSO（不碰游戏分配器, 最稳）
    n >  15  -> 调 sub_140129CA0 (std::string::assign), 由游戏负责堆分配

析构也由游戏负责释放 —— **同一个分配器，安全**。

## 自检

RegisterAll 在写内存之前逐条检查：

| 检查 | 不过就 |
|---|---|
| name / handler 非空 | 跳过该条 |
| argCount 在 [0,8] | 跳过该条 |
| name / usage / description <= 15 | 跳过该条 |
| argNames[i] <= 15 | 跳过该条 |

**宁可不注册也不冒险写入** —— 因为越界写会冲垮 +0x68 的 handler 指针，直接崩游戏。

## 集成

两个项目都在 hoi4plugins.sln 里。插件侧只需把 console_cmd.c 加进 ClCompile：

    plugin.vcxproj
      ClCompile: console_cmd.c, plugin_main.c, camera_height.c
      ClInclude: console_cmd.h, camera_height.h
