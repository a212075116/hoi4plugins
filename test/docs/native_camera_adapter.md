# 原生摄像机适配闭环测试

2026-10-14，生产DLL已接入，不再仅是外部Python原型。合同见[原生适配与功能状态](../../ai_docs/07_逆向能力/原生摄像机适配与功能状态.md)。

## 使用与部署

Release构建后部署 hoi4_mod_plugin.dll、hoi4_debug_console.exe；保留游戏根 hoi4plugins/bindings 下对应 SHA 的 .profile。
只有DLL而没有资料时，摄像机能力会明确拒绝，不退回旧RVA。资料仅启动加载，无热重载。
可用原游戏/外部控制台执行 plugin_camera_read（已知构建、单人执行上下文）；该命令不设置摄像机。
外部控制台 /filter function 只看功能状态；独立文件是游戏根 hoi4plugin_function_log.log。
未知构建未迁移旧模块全部阻断，只读原生API/监视与游戏命令注册是不同能力。

生成资料，项目根执行：

```powershell
python test/tools/prepare_native_camera_profile.py --image ../hoi4.exe --directory bindings
```

只为已验证布局自动生成 runtime_read=1；其他构建在 candidates 下输出禁用草稿。不要将格式通过当成布局审核。

## 原生夹具

在 VS2022 x64 Developer Command Prompt、项目根运行：

```bat
cl /nologo /EHsc /std:c++17 /O2 test/modules/camera/native_adapter_fixture.cpp /Fe:test/reports/20261014_native_camera/native_fixture.exe /Fo:test/reports/20261014_native_camera/native_fixture.obj /link bcrypt.lib shell32.lib
test\reports\20261014_native_camera\native_fixture.exe
test\reports\20261014_native_camera\native_fixture.exe --offline "D:\SteamLibrary\steamapps\common\Hearts of Iron IV\hoi4.exe"
```

夹具直接编译实际native_adapter.cpp，不是另一套解析器。101检查覆盖严格资料、RTTI/getter歧义、真实VirtualQuery/保护页、重复根、坏值、类型/代码变化、已知纠正通道、未知写阻断、批准只读不依赖旧模块及初始化发布/状态去重。
合成对象不冒充游戏实机。--offline对两个真实PE验证，未实例化第二映像。

启动门：

```powershell
python test/modules/camera/test_native_startup_gate.py . test/reports/20261014_native_camera/gate_manual
```

使用实际PluginThread函数体、受控业务callee，分别运行未知、已知、已知摄像机关闭及部分进程拦截模式。
未知旧版本调用19项，新版0项；已知正常均19。源状态三态及DLL/工具回滚见报告。
日志颜色执行 hoi4_debug_console.exe --status-color-self-test：7检查，绿色10、紫色13，背景保留。
原尾读/队列17检查、补全20检查通过；--read-only拒绝命令及空前缀补全，不连接旧bridge。

## 实机及记录

test/reports/20261014_native_camera 下保留：

- BASELINE_command / ROLLBACK_command：同一 plugin_camera_read 输入均 Unknown command、exit1；旧命令功能未因此判成坏。
- final_live_regression：读取与旧字段路径/外部原型一致；高度600、Effect设550/加25、范围调整再恢复310/50/3000；资料暂改后仍使用启动快照，文件哈希恢复。
- native_matrix：101检查与两个映像的原生定位stdout/stderr/exit。
- gate_baseline / gate_modified / gate_rollback：实际启动体的控制依赖测试。
- host_invalid_profile / helper_and_host：未知PE宿主实际加载DLL，资料拒绝与只读viewer命令阻断。
- modified_function_log / final_function_log：初始化、菜单拒绝、进入地图及能力变化；旧会话sentinel被新启动清除。
- build_release / build_debug、module_query、native_rollback：构建、模块身份及精确恢复。

初版导出声明链接不一致曾导致Release构建C2375，日志保留为build_linkage_error；修正后重新构建/测试，未把旧产物冒充新产物。
所有游戏关闭均正常CloseMainWindow并确认terminal，未用Frida或计时结束游戏；--logs-ms仅结束helper日志读取。
不执行正式存档保存、吞并或成就测试指令；原成就兼容的正常启动行为不被宣称完全没有Steam活动。
颜色数值/日志源已自动验证，主观GUI观感仍留用户目视。本轮不做多人实机或掉电测试。
