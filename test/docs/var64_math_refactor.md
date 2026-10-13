# 第四批定点算术与存储解码回归

2026-10-13。只验证源码整理，不附加游戏、不执行游戏命令、不改存档或成就。

## 存储路径与独立oracle

```powershell
python test/modules/effect/test_var64_decode_paths.py src/plugin/SDK_RVA/variable64/variable64.c OUTPUT_DIR
```

OUTPUT_DIR为独立目录，依赖VS2022 Community x64编译器。
夹具编译真实 `Var64_ReadStoredIn` 和新private计算模块，只有lookup依赖用模型替代。
Python任意精度整数独立计算三槽组合、范围与NULL输出模式，并独立判断查询序列，不使用C生产算法作为期望值。

固定种子20261015（不是执行日期），共21304条输入。
覆盖signed64两端、随机有效raw、非整槽、非法32位分量、坏fraction、缺frac/high/main、无container、坏名字及NULL输出。
观察值是返回码、raw输出/失败时哨兵保持，以及查询轨迹0/1/12/123。
BASELINE、MODIFIED、ROLLBACK各21304/21304符合oracle，同输入的stdout逐字节相同、stderr为空、exit0。
身份模式允许结构有效但不能完整取值的组合，专门保留，不以“更严格验证”为由改变旧规则。

## 定点算术

```powershell
python test/modules/effect/test_var64_raw_math.py src/plugin/SDK_RVA/variable64/variable64.c OUTPUT_DIR
```

三态10676/10676，包含边界组合与固定种子12026的10000条随机输入，符合Python整数oracle。
加减保持对称饱和；乘除保留整数128位中间值；除零原样返回失败。
旧单文件源码提取原函数，新版包含实际math头文件，不能用旧位置缺函数误判为算法删除。

## 连带回归

三态分别运行身份8/8、三槽2049/2049、语言名6/6、ROOT操作数、setter债务9/9。
上一批16696条文本/侧槽名称及31168条字段/语言桥接输入也重跑，保持输出与轨迹相同。
身份/三槽历史夹具兼容新计算头文件与旧单文件；生产算法没有另写一份在夹具中。
涉及容器、可读性、原生调用和hook的依赖仍是受控模型，不等于游戏或GUI实机验收。

## 构建与回滚

Debug/Release完整解决方案构建通过。
源码包、源码文件、DLL在独立修改副本上执行原ROLLBACK.sh，恢复到本轮基线字节/哈希；恢复源码重新编译并重复同输入。
修改版留在项目与归档，没有用回滚副本覆盖源码。
本轮不部署新DLL、不重启游戏，CURRENT_BUILD仍是游戏根已部署版本。
补充证据目录：`test/reports/20261013_var64_math_refactor/`。
四角色仍是 `test/reports/20261012_variable64_transaction/` 中MODIFIED_FILE.zip、DIFF_FILE.patch、VERIFICATION.txt及ROLLBACK.sh。
