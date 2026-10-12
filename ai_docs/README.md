# hoi4plugins 技术文档索引

本目录是整个 HOI4 插件工程的技术文档。**源码里不留注释，解释一律写在这里。**

## 当前进展入口

variable64 最新状态优先看 [当前状态与复现](09_脚本数值系统/当前状态与复现.md)。模块文章中的探索过程与历史待办不自动代表当前状态。

## 目录

| 目录 | 内容 |
|---|---|
| `01_工程与构建/` | 目录结构、构建方式、已知问题、**复现索引表** |
| `02_载体/` | 载体（tbb.dll）原理、CRT 时序、导出转发 |
| `03_插件/` | 插件加载、类结构验证 |
| `04_控制台指令/` | 表项结构、注册器、handler 签名、踩坑记录 |
| `05_工具链/` | idalib 常驻服务、**测试脚本索引**、**MinHook 集成与 hook 选型**、Frida 探针、崩溃排查、崩溃文件重定向、拦截 -debug 打开日志 |
| `06_游戏结构/` | CGameState、摄像机字段、类继承链、游戏日期（可写）、**日期界面显示链路与主动刷新**、CState 与 CResistance（**启用机制** / **修复实验** 分三篇） |
| `07_逆向能力/` | 有没有官方接口、虚表与 RTTI、全局槽与 Idler 状态机、虚表索引表、找 setter 的方法 |
| `08_Effect系统/` | Effect 系统结构、注册器 API、注册新 Effect（含**实测记录**）、本地化与工具提示、**日期 Effect 与指令** |
| `09_脚本数值系统/` | scalar64/Array64当前合约、存储、存读档、恢复/归属/中断/压力及历史证据 |
| `10_Trigger系统/` | Bool与typed模板、比较/tooltip、动态与原版数组隔离、多人协调事项 |

## Trigger 注册器

Bool、TRG_VALUE_DEF、TRG_VARIABLE_DEF和typed scope/tooltip适配已实现；Array64有专用operandReader。见[注册器 API](10_Trigger系统/注册器API与验证.md)、[数值块](10_Trigger系统/数值块模板与Scope适配.md)。

Array64已正式接入10个effect与1个trigger，使用[Array64单人交付说明](09_脚本数值系统/Array64单人交付说明.md)。功能主线基本完成；资源增长归因、GUI视觉、多人与掉电等发布检查仍未完成。
测试入口见[test/docs数值索引](../test/docs/numeric_system.md)，不要把旧CModule阶段“未开放API”当作当前状态。

## 约定

- 单个md严格不超过300行；超过按主题拆分，原入口保留链接，历史失败证据不删。
- 历史章节必须明确实验阶段与替代入口，过时操作步骤不作为当前推荐；本轮复核记录见[文档核对](01_工程与构建/文档核对与维护约定.md)。
- 每篇文档必须写清**依据**（IDA 函数名 / RVA / 运行时实测日志）。
- 任何"尚未验证"的东西必须显式标注，不能写成结论。

## 外部参考

| 来源 | 用途 |
|---|---|
| https://github.com/MyresMkG/HOI4-Mod-Injector | CRT 探测与时序策略的参考实现 |
| https://github.com/Joey0x646576/nativeaot-function-calling-example | NativeAOT 注入原生进程（本项目评估后未采用） |
| https://learn.microsoft.com/en-us/windows/win32/dlls/dllmain | DllMain 的 Windows 限制 |
