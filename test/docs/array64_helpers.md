# Array64记录与所有权键三态回归

2026-10-14，第十五批，私有纯计算收拢，记录格式与恢复不变。

## 入口

从项目根执行：

```powershell
python test/modules/effect/test_array64_helpers.py SOURCE_ROOT OUTPUT
python test/modules/effect/test_array64_durable_native.py OUTPUT [SOURCE_ROOT]
python test/modules/effect/test_array64_ownership_native.py OUTPUT [SOURCE_ROOT]
python test/modules/effect/test_array64_shape_native.py OUTPUT [SOURCE_ROOT]
python test/modules/effect/test_array64_journal_native.py OUTPUT [SOURCE_ROOT]
```

新增helper夹具以Python独立生成小端、signed和FNV oracle，并检查写入canary及所有权键。
基线使用真实旧函数及内联表达式的文本投影；修改版直接包含两个生产头文件。
投影检查不替代导入/导出的生产调用，因此另跑四组真实存储代码与受控native适配器夹具。
四组旧入口保留单参数用法；可选源根便于基线/回滚，新增私有头文件在展开源中内联，AST辅助常量未改动。

| 同输入检查 | BASELINE | MODIFIED | ROLLBACK |
|---|---|---|---|
| wire/owner oracle | 8000/4000组，168000项 | 同左 | 同左 |
| durable | 411/411 | 411/411 | 411/411 |
| ownership | 211/211 | 211/211 | 211/211 |
| shape | 287/287 | 287/287 | 287/287 |
| journal | 244/244 | 244/244 | 244/244 |

五组实际stdout、stderr和退出状态三态一致，均exit0。
另从实际导出夹具保存binary golden：大型baseline98393字节、owned98449字节及journal记录，完整SHA三态一致。
包含损坏/截断/版本错误、scope/lineage/owner拒绝、4096元素、失败隔离、恢复重试、receipt/nonce与回放保护等既有检查。
不可把受控写入适配器当作新实机磁盘、掉电或多人验收。

## 归档

报告：`test/reports/20261014_array64_helpers/`，保留全项目自有源码清单、原始基线、三态、golden记录、通用回归、构建和最终验证。
持续复用 `test/reports/20261012_variable64_transaction/`四角色：
`MODIFIED_FILE.zip`、`DIFF_FILE.patch`、`VERIFICATION.txt`、`ROLLBACK.sh`。
回滚脚本对 `*.array64-helpers.zip`或 `*.array64-helpers.dll`副本恢复本批基线；完整包另验证binary patch重建及最初基线回滚。
新DLL只归档，未部署或运行游戏。
机制说明见[Array64记录与所有权键模块](../../ai_docs/09_脚本数值系统/Array64记录与所有权键模块.md)。
