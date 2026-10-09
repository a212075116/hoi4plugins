# Frida 探针

> 脚本目录：hoi4plugins/test/（原 flirt/loader/，已迁移）

## 用途

静态分析给出"结构长什么样"，Frida 给出"运行时它到底是什么"。
两者一致才算数。

## 宿主

flirt/loader/frida_host.py 提供：

| 函数 | 说明 |
|---|---|
| find_pid() | 找 hoi4.exe 进程 |
| connect(js_path, force_spawn) | **attach** 到已运行进程（不 kill）；返回 (pid, session, sc, fresh) |
| wait_game_ready(session, ...) | 基于 CGameState 的等待（推荐） |
| wait_stable(...) | 旧的轮询等待（仅在 st 返回 chi 时用） |

## 硬规则：绝不同时开两个 Frida 会话

同一个 hoi4.exe 上开两个会话会把游戏搞死（实测过一次，pid 53864 死亡）。

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

探针脚本大量硬编码 RVA，**游戏版本一变就全部作废**。
没有加版本校验。
