# CRT 时序问题（本工程最难的一处）

> 源码：src/carrier/carrier_loader.cpp

## 症状

如果直接在 DllMain(DLL_PROCESS_ATTACH) 里 CreateThread，进程会**以 0xC0000409 (BEX64) 死掉，连窗口都没有**。

## 原因

游戏静态链接了 MSVC CRT。CRT 会给**每个新线程**调 TLS 回调来分配 per-thread 数据，
该回调依赖 CRT 启动时分配的一个**进程级 TLS 索引**。

若某条线程的 TLS 回调**先于**该索引存在而运行，CRT helper 返回 NULL，
调用方直接 abort() —— 实现为 __fastfail(7)：

    mov ecx, 7
    int 29h

表现为进程以 0xC0000409 退出。

## 什么时候会踩到

| 启动方式 | 会不会踩 |
|---|---|
| 直接 Start-Process | 几乎不会——主线程通常已跑完 CRT 初始化 |
| Steam / Paradox Launcher 拉起 | **会**。进程以**挂起状态**创建，由 Steam 覆盖层挂进去的线程替游戏走完导入表，而游戏主线程还没被恢复，我们那条线程就先死了 |

## 处理方式

**只在确认 CRT 已就绪后才建线程**，从两处能被叫醒：

| 叫醒点 | 说明 |
|---|---|
| DLL_THREAD_ATTACH | 游戏自己起了新线程。能收到这个通知，本身就说明该线程已走过它自己的 TLS 回调 |
| 回调定时器 | 加载线程进入消息循环后 |

两者都需 CRT 就绪；等不到就在**当前已初始化的线程**上直接跑（建线程才危险）。

## CRT 就绪怎么判定

pdata 段 + 代码扫描的组合：pdata 给出准确的函数边界，然后

    abort() = 内联的 __fastfail(7)（mov ecx,7 / int 29h）
    -> 找"NULL 检查后调 abort"的调用点
    -> 那个 guard 之前被调用的函数 = per-thread data helper
    -> 验证形状，只有唯一候选才采信

对应检测：cmp dword ptr [rip+disp], -1（"CRT 是否已分配索引"）。

**多个匹配说明形状不够特异，不能信**，此时退回"按时间等"的老路子。

## 参考

https://github.com/MyresMkG/HOI4-Mod-Injector 的 src/crtprobe.cpp、src/dllmain.cpp
—— 探测形状与时序策略与该工程一致。
