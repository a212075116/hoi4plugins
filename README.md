# hoi4plugins

HOI4 1.19.3、Windows x64 原生插件工程：提供脚本数值扩展、Effect/Trigger 注册、外部控制台与成就兼容功能。

**这是与游戏版本强绑定的工程，不是跨版本 SDK。** 更新游戏后必须重新核对 RVA、结构和运行行为；编译成功不代表其他版本可用。

## 从哪里开始

| 任务 | 入口 |
|---|---|
| 理解模块与构建 | [目录结构](ai_docs/01_工程与构建/目录结构.md)、[构建方式](ai_docs/01_工程与构建/构建方式.md) |
| 查看已交付功能与证据 | [技术文档索引](ai_docs/README.md)、[测试索引](test/docs/README.md) |
| 修改代码而不改变行为 | [源码简化与维护约定](ai_docs/01_工程与构建/源码简化与维护约定.md) |
| 复现本轮简化的回归 | [源码重构回归](test/docs/source_refactor.md) |

## 三个构建模块

- `src/carrier/`：构建 `tbb.dll`，转发原版导出并负责加载插件。
- `src/plugin/`：构建 `hoi4_mod_plugin.dll`，游戏内功能按 `SDK_RVA/` 子目录分工。
- `src/debug_console/`：构建 `hoi4_debug_console.exe`，独立进程的日志显示、输入、只读补全查询。

公共插件日志在 `src/plugin/SDK_RVA/common/log.c`；它不承担游戏日志读取或载体启动日志职责。

## 构建

环境：Visual Studio 2022 Community、v143、Windows SDK 10.0.26100.0。
在 Developer Command Prompt 中，从仓库根目录运行：

```bat
msbuild hoi4plugins.sln /p:Configuration=Release /p:Platform=x64
```

产物在 `build/Release/`。构建不会部署，也不会替换正在运行的游戏所加载的 DLL。
不要在游戏运行中覆盖 DLL；部署前保存并退出，再核对产物哈希。
`tbb_real.dll` 保持原版，不应随插件重构被修改。

## 修改前必须知道

- `.c` 是 C 源，外部控制台与载体为 C++17；不要把整个工程统一改成 C++。
- 自有源码使用 ASCII，不留解释性注释；第三方源码保持原样；行为、依据和失败模式写进 `ai_docs/`。
- 单篇技术/测试文档不超过 300 行，长内容按职责拆分并保留索引。
- 合并代码必须保留分配器、对象所有权、线程、scope、权限与故障恢复语义。
- 多人禁用外部控制台指令；单人铁人和开发者指令权限按现有实现保留。
- 游戏成就条件仍由原版判断；兼容功能不是批量赠送成就。
- `test/` 不参与生产构建，测试报告在 `test/reports/`；报告与二进制不纳入 Git。

目前完成前六批行为保持重构，不表示整个项目已完成规范化；大型数值后端和 hook 生命周期仍需要分批处理。
