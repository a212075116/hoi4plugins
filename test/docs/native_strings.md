# 第八批原生字符串布局与策略回归

2026-10-14。只编译源码/恢复副本，不调用游戏载入函数，不操作存档或成就。

## 2160条固定输入

```powershell
python test/modules/console/test_native_string_policies.py SOURCE_ROOT OUTPUT_DIR
```

SOURCE_ROOT包含src，OUTPUT_DIR独立，依赖VS2022 Community x64编译器。
实际Console短串/长串/SetMessage与Var64_WriteSaveFileName函数参与编译，不在模型中重新实现生产策略。
原生assign、模块与地址可读性依赖为模型，记录调用次数和赋值长度，不证明真实游戏分配器行为。
旧data选择表达式直接取自Effect_BuildTooltip，新版直接调用真实NativeString_Data。

覆盖空/NULL、15/16、119/120/121、159/160/511字节、cap=0/15/16/127、缺模块、地址不可读。
额外覆盖源指向目标buf或size元数据的别名，防止“合并赋值”改变写入先后。
比较完整32字节字段，只有模型assign产生的动态地址按固定指针身份归一化；其他字段和未写区域保留原值。
112条独立data选择期望涵盖cap=0/14/15/16/127/4095/4096/UINT64_MAX、异常size与NULL外部ptr，确认只选择、不验证、不改字段。
BASELINE、MODIFIED、ROLLBACK同输入的2160条输出逐字节相同，stderr为空，exit0。

## 连带回归

三态Bool22/22、typed27/27、tooltip16/16、console日志/字符串17/17通过，输出/失败状态一致。
全部11套数值、字段、债务、存储与Effect注册夹具在当前源码重跑通过。
save helper只替换同义assign声明/RVA符号，loadgame其余函数体、scope与恢复流程未改变。
布局/模型通过不等于实机原生对象、真实存档载入或GUI验收。

## 修正与恢复

新夹具初次元数据dict遗漏result=导致Python语法错误exit1；补充真实表达式所需SSO常量前编译exit2；错误记录保留，生产源码未因夹具错误改变。
Debug/Release解决方案构建通过；独立源码zip与DLL回滚到本轮原始字节/哈希，恢复目录重编译并重跑同输入。
修改版保留，未覆盖游戏根部署文件、未重启游戏。
补充目录 `test/reports/20261014_native_strings/`；四角色仍用原事务目录 `test/reports/20261012_variable64_transaction/`。
