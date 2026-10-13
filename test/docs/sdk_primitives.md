# 第七批SDK基础机制回归

2026-10-14。验证通用内存检查迁移与16字节借用名称view，不启动、附加或执行游戏指令。

## 内存范围三态

```powershell
python test/modules/console/test_native_memory.py SOURCE_ROOT OUTPUT_DIR
```

SOURCE_ROOT为包含src的项目/基线/恢复目录，OUTPUT_DIR独立；依赖VS2022 Community x64。
编译真实ConsoleCmd_IsReadable；新版同时包含真实native_memory.c，旧入口作为兼容转发也受测。
固定seed20261018只是seed，13342条输入对照独立整数/保护位oracle，记录返回值与VirtualQuery调用次数。
NULL、零长度、committed/reserved/free、read/writecopy/execute组合、guard/noaccess、末端、跨界及地址回绕覆盖。
另用实际VirtualAlloc/VirtualProtect在夹具进程内验证14条边界和保护模式，不读取游戏进程。
BASELINE、MODIFIED、ROLLBACK：13342/13342、实际页面14/14、同输入stdout一致、stderr为空、exit0。

## 借用名称view

```powershell
python test/modules/effect/test_native_name_view.py EFFECT_SOURCE_FILE OUTPUT_DIR
```

编译实际Effect_AddToken，底层AddToken/模块/可读性为模型，读取实际传入view的data和偏移8处长度。
720条输入涵盖空/NULL、15/16/63/64/511/512字节、NULL输出、模块/地址失败、token返回0/正/负值。
三态720/720符合独立期望，同输入输出一致；未复制借用data或改变调用方验证策略。
console拥有字符串的assign/SSO回归另行保留，不以view测试替代它。

## 注册器与数值连带回归

```powershell
python test/modules/trigger/test_trigger_registry_native.py OUTPUT_DIR --source TRIGGER_SOURCE_FILE
python test/modules/trigger/test_typed_trigger_native.py OUTPUT_DIR TRIGGER_SOURCE_FILE
python test/modules/trigger/test_typed_tooltip_native.py TRIGGER_SOURCE_FILE OUTPUT_DIR
python test/modules/console/run_source_refactor_regression.py --source-root SOURCE_ROOT --output OUTPUT_DIR --phase PHASE
```

旧调用形式仍有效。三态Bool22/22、typed27/27（含150项极值比较）、tooltip16/16、console日志/字符串17/17，literal stdout/stderr/exit一致。
Trigger夹具保留原受控可读性模型并适配新入口；真实common检查由前述内存测试独立覆盖，不冒充游戏实机。
全部11套现有数值/字段/债务/Effect注册夹具在当前源码重跑通过；本轮variable64生产源码哈希未变化。

## 修正与恢复记录

迁移初次编译遗漏Effect的view.len字段名，修正为size；失败构建exit1保留。
名称view夹具初次占位符替换误改RVA_ADD_TOKEN，旧/新夹具编译exit2，已改为只替换独立标记行；未因此改变生产算法。
Debug/Release构建通过；独立源码zip与DLL副本回滚到本轮原始字节/哈希，恢复目录重编译并重跑同输入。
原四角色仍在 `test/reports/20261012_variable64_transaction/`；补充证据在 `test/reports/20261014_sdk_primitives/`。
当前游戏根部署文件未覆盖，新DLL仅构建/归档；不把构建通过当作已部署。
