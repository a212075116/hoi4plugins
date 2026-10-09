# hoi4plugins 技术文档索引

本目录是整个 HOI4 插件工程的技术文档。**源码里不留注释，解释一律写在这里。**

## 目录

| 目录 | 内容 |
|---|---|
| `01_工程与构建/` | 目录结构、构建方式、已知问题、**复现索引表** |
| `02_载体/` | 载体（tbb.dll）原理、CRT 时序、导出转发 |
| `03_插件/` | 插件加载、类结构验证 |
| `04_控制台指令/` | 表项结构、注册器、handler 签名、踩坑记录 |
| `05_工具链/` | idalib 常驻服务、Frida 探针、崩溃排查、崩溃文件重定向、拦截 -debug 打开日志 |
| `06_游戏结构/` | CGameState、摄像机字段、类继承链 |
| `07_逆向能力/` | 有没有官方接口、虚表与 RTTI、全局槽与 Idler 状态机、虚表索引表、找 setter 的方法 |
| `08_Effect系统/` | Effect 系统结构、注册器 API、注册新 Effect、本地化与工具提示 |

## 约定

- 单个 md 不超过 300 行（硬上限 400）。
- 每篇文档必须写清**依据**（IDA 函数名 / RVA / 运行时实测日志）。
- 任何"尚未验证"的东西必须显式标注，不能写成结论。

## 外部参考

| 来源 | 用途 |
|---|---|
| https://github.com/MyresMkG/HOI4-Mod-Injector | CRT 探测与时序策略的参考实现 |
| https://github.com/Joey0x646576/nativeaot-function-calling-example | NativeAOT 注入原生进程（本项目评估后未采用） |
| https://learn.microsoft.com/en-us/windows/win32/dlls/dllmain | DllMain 的 Windows 限制 |
