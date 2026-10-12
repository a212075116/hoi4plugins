# Frida 探针

> 脚本目录：hoi4plugins/test/
> 宿主在test/lib/frida_host.py，公共JS在test/lib，模块探针在test/modules/；probes目录仅历史
> （早期路径为 flirt/loader/，**该目录已不存在**）

## 用途

静态分析给出"结构长什么样"，Frida 给出"运行时它到底是什么"。
两者一致才算数。

## 宿主

test/lib/frida_host.py提供：

| 函数 | 说明 |
|---|---|
| find_pid() | 找 hoi4.exe 进程 |
| connect(js_path, force_spawn) | 已有PID且force_spawn=False时attach；无PID或强制时会spawn/重开；返回四元组 |
| wait_game_ready(session, ...) | 基于 CGameState 的等待（推荐） |
| wait_stable(...) | 旧的轮询等待（仅在 st 返回 chi 时用） |

## 硬规则：绝不同时开两个 Frida 会话

历史双会话实验中进程死亡；这是风险记录，不证明任何双会话必然崩溃。现有驱动优先复用单会话，避免未经管理的并发/快速切换。

## 保留字陷阱

Frida 里不能声明名为 hexdump 的全局变量：

    TypeError: cannot define variable 'hexdump'

改名为 dumpBytes 即可。

## 字符串读取陷阱

Frida 的 readUtf8String(size) **不会在 NUL 处停止**。
正确做法是读 readByteArray(n) 再按 0 截断。

## 本工程验证过的东西

| 项 | 结果 |
|---|---|
| 命令表 count（注册前后） | 380 -> 381 -> 385 |
| 新命令表项内容 | name/desc/handler 全部与注册日志一致 |
| 摄像机字段 | 用户用 CE 逐项实测（Frida 只做确认） |
| L10 类结构 | 与静态 RVA 一致 |

## 注意

探针脚本大量硬编码 RVA，**游戏版本变化必须重新核对**。
没有加版本校验。
