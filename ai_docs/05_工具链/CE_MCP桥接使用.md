# Cheat Engine MCP 桥接：用法与在 HOI4 逆向中的实战

> 本文档只记录**已验证**的用法。配套的接入与验证过程见
> 外部桥接安装记录（当前仓库未收录，不作为本项目可打开/执行的入口）（那份是安装记录，本文是使用手册）。

## 为什么用它（和 Frida 的分工）

| | Frida | CE MCP 桥接 |
|---|---|---|
| 附加方式 | attach 进游戏进程 | CE 作为独立进程读写内存 |
| 对游戏的影响 | 历史某些attach/hook测试曾退出，不是工具必然崩溃 | 无进程内注入不等于无风险；错误写入/断点仍能导致游戏异常 |
| 能做什么 | hook、调用函数、读栈 | 读写内存、内存扫描、Lua 脚本、设断点 |
| 适合 | 需要 hook 的场合 | **查字段、验证读写语义、定位谁在写** |

**结论：能用 CE 验证的，就不要用 Frida。** 本次定位「摄像机画面不更新」的根因，
就是靠 CE 一次实验完成的，而此前用 Frida + 改插件绕了很久。

## 环境事实

| 项 | 值 |
|---|---|
| CE | 7.6.0.8629（`C:\Users\a2120\Desktop\Cheat Engine\`） |
| 桥接仓库 | `C:\Users\a2120\Desktop\Cheat Engine\cheatengine-mcp-bridge` |
| MCP 服务端 | `<repo>\MCP_Server\mcp_cheatengine.py`（**175 个工具**） |
| venv | `<repo>\.venv\Scripts\python.exe`（mcp 1.30.0 + pywin32 312） |
| 命名管道 | `\\.\pipe\CE_MCP_Bridge_v99` |
| 自动加载 | `CE\autorun\ce_mcp_bridge_autoload.lua` |

**硬性要求**：CE → Settings → Extra → **取消勾选 "Query memory region routines"**，
否则扫描受保护页面可能蓝屏（CE 仓库 issue #760）。

## 自写调用器 `work/refs_probe/ce_call.py`

仓库自带的探针只能发**空参数**的工具调用，不够用。自写的这个支持任意参数：

```
<repo>\.venv\Scripts\python.exe ce_call.py '<工具名>|<JSON参数>;;<工具名>|<JSON参数>'
```

它内部做的是：拉起 MCP 服务端 → `initialize` → `notifications/initialized` →
依次 `tools/call` → 打印每个工具的返回 → 结束进程。多个调用用 `;;` 分隔。

## 三个核心工具

### 1) `open_process` —— 附加游戏

```
ce_call.py 'open_process|{"process_id_or_name":"hoi4.exe"}'
```

返回 `{"process_name":"hoi4.exe","process_id":43428,"success":true}`。
**游戏每次重启后都要重新执行这一步**（CE 会与旧进程断开）。
用 `get_opened_process_id` 确认当前附加对象。

### 2) `create_thread` —— 执行任意 Lua（读写内存的主力）

```
ce_call.py 'create_thread|{"code":"<lua 代码>"}'
```

**异步执行**，返回 `{thread_id, success}`。代码里的全局变量可以用
`_G.名字 = 内容` 存在 CE 的 Lua 状态里，然后用下一个工具取回来。

### 3) `get_global_variable` —— 取回 Lua 里存的结果

```
ce_call.py 'get_global_variable|{"name":"DSHCAM"}'
```

返回 `{"value":"...","success":true}`，`value` 是字符串。

**「create_thread 写入 → get_global_variable 读出」这个组合就是这套桥接最实用的用法**，
它让任何内存读写在 Python 侧都变成可控的同步操作。

## 实战 Lua 片段（摄像机，已实测）

```lua
local base = getAddress('hoi4.exe')
local obj  = readPointer(base + 0x332F698)
local cam  = readPointer(obj + 0x750)
local t = {}
t[#t+1] = string.format('cam=%X', cam)
t[#t+1] = 'A.y=' .. string.format('%.2f', readFloat(cam + 0x678))
t[#t+1] = 'B.y=' .. string.format('%.2f', readFloat(cam + 0x684))
t[#t+1] = 'D.y=' .. string.format('%.2f', readFloat(cam + 0x69C))
t[#t+1] = 'in1.y=' .. string.format('%.2f', readFloat(cam + 0x194))
t[#t+1] = 'lo=' .. tostring(readInteger(cam + 0x6D0))
_G.DSHCAM = table.concat(t, '  ')
```

写值同理，把 `readFloat` 换成 `writeFloat(地址, 值)`。

## 已实测的返回（2026-10-10）

```
cam=1BB406C75C0  A.y=2500.01  B.y=2500.01  D.y=2500.00
in1.y=2500.01  in2.y=2500.01  in3.y=2500.01  lo=2500  hi=4000
```

**由此验证的结论**：`in1.y` 恒等于 `B.y` —— 与反编译推断的
`*(a1+0x190) = *(a1+0x680)`（视图矩阵输入 ← B 组）完全吻合。
静态分析结论可以用这套工具当场证实，不必猜。

## 踩过的坑

| 现象 | 原因 | 处理 |
|---|---|---|
| `No process attached` | 没先 `open_process` | 先附加，游戏重启后要重附 |
| `read_integer` 传 `float` 报 `number has no integer representation` | 桥接的 Lua 侧对浮点用 `format %X`，会失败 | **改用 `create_thread` + `readFloat`** |
| `read_pointer_chain` 的 `offsets` 传 `'0x750'` 报错 | 参数要求**整数** | 传十进制 `1872` |
| `read_pointer_chain` 返回的 `final_value` 看着是天文数字 | 它按 64 位原始整数读，float 字段会被误读 | 只用它**取指针链中间地址**，值用 `readFloat` 另读 |
| `get_symbol_address` 传 `name` 报缺字段 | 参数名是 `symbol` | `{"symbol":"..."}` |
| 输出中文乱码 | 控制台编码 | 调用前设 `$env:PYTHONIOENCODING='utf-8'` 与 `[Console]::OutputEncoding` |

## 其它可用工具（175 个里的常用项）

| 工具 | 用途 |
|---|---|
| `read_memory` / `write_memory` | 原始字节读写 |
| `read_string` / `write_string` | 字符串 |
| `scan_all` / `next_scan` / `get_scan_results` | 内存扫描（找值在哪） |
| `aob_scan` | 按字节特征扫描 |
| `enum_modules` | 模块基址列表 |
| `get_address_info` | 地址 → 符号/模块（反查字段归属） |
| `get_thread_list` | 线程列表 |
| `list_breakpoints` | 已设断点 |
| `get_memory_record` / `set_memory_record_value` | 操作 CE 地址列表 |

## 用它能做的下一步（尚未做）

1. **找「谁在写某个地址」**：CE Lua 有 `debug_setBreakpoint`，可以用
   `create_thread` 设内存写断点，记录写入者的 RIP 与调用栈。
   这是定位「每帧覆盖我们写入值的那段代码」的正规手段。
2. **内存扫描定位字段归属**：用 `scan_all` 从一个已知值反查它在哪个结构里。

## 相关文档

| 主题 | 文档 |
|---|---|
| 桥接安装与端到端验证 | 外部桥接安装记录（当前仓库未收录，不作为本项目可打开/执行的入口） |
| 摄像机字段与三个视图 | `hoi4plugins/ai_docs/06_游戏结构/摄像机字段.md` |
| 探针脚本总览 | `hoi4plugins/test/docs/README.md` |
