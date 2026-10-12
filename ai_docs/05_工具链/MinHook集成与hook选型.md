# MinHook 集成与 hook 选型

> MinHook 位置：`src/plugin/SDK_RVA/minihook/`
> 来源 https://github.com/TsudaKageyu/minhook（commit `8af6b4a`，**BSD 2-Clause**，见该目录 `LICENSE.txt`）。
> 已删除其 `.git`，随本仓库管理。

## 参与编译的文件（x64 只需这些）

    src/plugin/SDK_RVA/minihook/src/hook.c
    src/plugin/SDK_RVA/minihook/src/buffer.c
    src/plugin/SDK_RVA/minihook/src/trampoline.c
    src/plugin/SDK_RVA/minihook/src/hde/hde64.c

封装在 `SDK_RVA/hook/inline_hook.c`：

| 函数 | 说明 |
|---|---|
| `InlineHook_Init()` | 调 `MH_Initialize`，只做一次 |
| `InlineHook_Install(target, detour)` | `MH_CreateHook` + `MH_EnableHook`，返回 original |
| `InlineHook_Remove(target)` | 卸载 |

## ⚠️ 选型结论：不是所有 hook 都该换成 MinHook（实验证明）

### 两种 hook 的本质差别

| | IAT hook | inline hook (MinHook) |
|---|---|---|
| 改什么 | 本模块**导入表**里的函数指针 | 目标函数**入口的机器码** |
| 影响范围 | **只有本模块**的调用 | **全进程**所有调用 |
| 能拦什么 | 只能是导入的函数 | 任意函数 |
| 对 kernel32 本体 | 不动 | 改动，**包括系统/自身调用** |

### 实测结果

把 `file_redirect.c`（`CreateFileW/A`、`CreateDirectoryW/A`）从 IAT 改成 MinHook：

    [hook] installed at 00007FFCA72A70F0, orig=...   ; CreateFileW 成功
    [hook] installed at 00007FFCA72A70B0, orig=...   ; CreateFileA 成功
    -> 装第 3 个 (CreateDirectoryW) 时游戏直接退出

**原因**：MinHook 安装后续 hook 时自身也要用文件 API（挂起/恢复线程、读写内存），
而它已经把全进程的 `CreateFileW` 接管了 —— 于是陷入自己的陷阱。
加递归保护也解决不了，因为**崩溃发生在安装阶段**，不在回调里。

把 `file_redirect.c` 回滚成 IAT 后，同样构建下游戏稳定，
而 `process_block.c` 用 MinHook 一切正常：

    [redir] installed  W=... A=... DW=... DA=...       ; IAT, 稳定
    [hook] installed at 00007FFCA7294F70                ; CreateProcessA (MinHook)
    [hook] installed at 00007FFCA728C680                ; CreateProcessW (MinHook)
    [pblock] installed via MinHook A=... W=...          ; 正常
    [hook] installed at 00007FF6C7971EE0                ; 游戏内部函数 (MinHook)
    游戏存活 ✓

### 最终方案（混合）

| 模块 | 方式 | 理由 |
|---|---|---|
| `file_redirect.c`（文件 API） | **保留 IAT** | 只需拦游戏自己的调用；inline 会波及全进程并导致安装阶段自陷 |
| `process_block.c`（CreateProcess） | **MinHook** | 需要拦所有来源的调用，且不涉及 MinHook 自身用到的 API |
| `gamedate_ui.c`（游戏内部函数） | **MinHook** | 游戏内部函数没有 IAT 槽位，**必须** inline |

## 递归保护（inline hook 必配）

inline hook 下，回调里做的任何事（例如 `Plugin_Log` 写日志文件）**也会再次进入 hook**，
形成 回调 → 写文件 → CreateFileW → 回调 的循环。

做法（`SDK_RVA/hook/hook_guard.h` + 各回调）：

```c
extern __declspec(thread) int g_hookReentry;   // 线程局部

// 回调开头：
if (g_hookReentry > 0) return g_origXxx(...);  // 递归中，直接转发
++g_hookReentry;
...                                            // 判断/日志
--g_hookReentry;
```

注意：**必须在调用 original 之前把计数减回去**，否则 original 内部的合法调用会被误判为递归。
