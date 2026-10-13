# 日期解析边界三态回归

2026-10-14，第十三批：修正溢出、NULL游标和失败游标提交。

## 运行

从项目根执行：

```powershell
python test/modules/gamedate/test_gamedate_parser.py SOURCE_ROOT OUTPUT --optimization Od
python test/modules/gamedate/test_gamedate_parser.py SOURCE_ROOT OUTPUT --optimization O2
```

两种模式使用不同输出目录；源根须含完整src树。需要MSVC x64工具链。
脚本以AST读取已有日期/UI夹具的字面量，复用其20000日期、4000加时间和140参数矩阵，不复制另一份生产逻辑。
追加24036组整数oracle、两组NULL异常捕获、空串和六组非法日期原子性检查。
语料种子20261014、输入哈希固定；每次保存原始输入、实际源码引用、编译及执行输出。

| `/Od`和 `/O2`分别观察 | BASELINE | MODIFIED | ROLLBACK |
|---|---|---|---|
| 编译 | exit0 | exit0 | exit0 |
| 执行断言 | 240724项、24032失败 | 240724项、0失败 | 恢复24032失败 |
| 执行状态 | exit1 | exit0 | exit1 |
| NULL游标/文本 | 异常被SEH捕获 | 无异常、返回-1 | 恢复旧异常 |
| 六组超范围日期 | 四组被接受 | 全部拒绝 | 恢复旧接受 |
| 非法日期不写状态/不刷新 | 四组失败 | 六组均通过 | 恢复旧失败 |

基线与回滚完整stdout一致；修改版两种优化模式完整stdout一致，stderr均为空。
基线exit1是断言失败，不是未捕获的进程崩溃；SEH只用于夹具保留旧NULL故障证据，生产代码没有新增异常吞掉机制。
另跑原有合法日期/UI夹具三态输出完全一致：192637项零失败，内存检查次数208304，摘要10827580189841091891。
注册器、数值、摄像机和console/log夹具三态一致，Debug/Release通过。
独立源码包和DLL副本回滚恢复基线哈希，工作区保留修改版。

## 归档与限制

报告目录：`test/reports/20261014_gamedate_parser/`；保存基线、三态两种优化结果、通用回归、scope guard、构建和最终验证。
持续复用 `test/reports/20261012_variable64_transaction/` 下的
`MODIFIED_FILE.zip`、`DIFF_FILE.patch`、`VERIFICATION.txt`、`ROLLBACK.sh`。
脚本接受 `*.gamedate-parser.zip`、`*.gamedate-parser.dll`副本，恢复本批基线；完整包另验证补丁重建及最初基线回滚。

没有部署或运行游戏。INT极值的加时间、float转整数及实际GUI不属于本批新验收，下一步继续检查月份归一化与加法边界。
设计见[日期整数解析边界](../../ai_docs/03_插件/日期整数解析边界.md)。
