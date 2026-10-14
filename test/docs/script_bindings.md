# 第二轮脚本注册基础测试

2026-10-14。合同见[脚本注册基础绑定](../../ai_docs/07_逆向能力/脚本注册基础绑定.md)。

## 使用

部署新版DLL还需要bindings/<SHA>.registry；摄像机.profile仍独立。缺失或错误资料显示script.bindings不可用并跳过整个脚本注册组。
已有单人地图可执行plugin_script_bindings；不创建变量、不调用factory、只报告已经发布的绑定。
未知构建未迁移业务依然阻断；通过模板定位不表示所有业务允许调用。

生成迁移候选，项目根：

```powershell
python test/tools/migrate_script_bindings.py --baseline-image ../hoi4.exe --image ../hoi4.exe.backup --output-directory test/reports/20261014_script_adapter/migration_backup
```

依赖Python pefile/capstone。不同SHA永远禁用，未解析数据地址置0，不按全局偏移猜；13唯一函数候选也须审核。

## 原生夹具

VS2022 x64 Developer Command Prompt，项目根：

```bat
cl /nologo /EHsc /std:c++17 /O2 test/modules/trigger/native_script_bindings_fixture.cpp /Fe:test/reports/20261014_script_adapter/native_fixture.exe /Fo:test/reports/20261014_script_adapter/native_fixture.obj /link bcrypt.lib shell32.lib
test\reports\20261014_script_adapter\native_fixture.exe "D:\SteamLibrary\steamapps\common\Hearts of Iron IV\hoi4.exe" bindings\7dc947be34970da1e1c787bcddbe7f62b610ff258aebf8f06aa8b348f3a031d5.registry
test\reports\20261014_script_adapter\native_fixture.exe "D:\SteamLibrary\steamapps\common\Hearts of Iron IV\hoi4.exe.backup"
```

实际native_adapter.cpp和script_bindings.inc；当前23检查，backup5检查。重定位映像是受控内存，不冒充游戏实机。
覆盖factory对象大小变化、所有模板/entry指针与代码、统一allocator、资料、失败原子发布及不绕过legacy门。

## 回归与证据

test/reports/20261014_script_adapter保存native_*输出、bool/typed/scalar/array/bootstrap/tooltip/scoped/camera结果、两个迁移报告及实际游戏命令。
Bool24/typed29新增绑定失败的就绪/实例/Scope拒绝；fixture映射旧地址只作为受控依赖，不代表生产保留固定地址。
旧函数体与新函数体的三态仍沿用同一输入；SourceBaseline/DLL副本与既有ROLLBACK.sh用于精确恢复。
plugin_script_bindings旧DLLUnknown command，新DLLSCRIPT_BINDINGS_READY，回滚旧DLL恢复Unknown command。

测试错误：初版DWORD引用与unsigned int类型不匹配（C2664）已修正；迁移器pefile.DATA_DIRECTORY拼写错误已修正；启动夹具新增分支缺局部i（C2065）已补，日志保留。
不存在的multiply_variable64输入及失败后变量未初始化导致的比较no，不算功能通过。正确原版add_to_variable ROOT及变量块比较yes另有实际输出。
分组同输入旧/新版custom add_to_variable64 ROOT均得12，原版add_to_variable ROOT均得12.5；custom路径保留为旧限制，不宣称数值通过。独立串行eval旧版的语义异常单独保留，未归因。
F1未新增free；没有多人、断电、未知映像实机或所有未来ABI保证。
