# Tail与共享句柄三态回归

2026-10-14，第十七批。

## 命令

从项目根执行：

```powershell
python test/modules/console/test_tail_handles.py SOURCE_ROOT OUTPUT
python test/modules/console/test_catalog_handles.py SOURCE_ROOT OUTPUT
```

源根须含完整src，输出独立目录；需要MSVC C++17 x64。
Tail夹具提取实际struct及方法，共用catalog fixture中的分配故障字面量，以AST读取、不执行脚本体。
模拟文件API和字节内容，保存行长度/内容hash、offset/id/volume、partial/sentinel及读/关闭调用摘要。

| 观察 | BASELINE | MODIFIED | ROLLBACK |
|---|---|---|---|
| 18个普通路径 | 输出/状态/调用摘要 | 完全相同 | 完全相同 |
| 3个异常文件句柄 | 各残留1个 | 全部释放 | 恢复旧残留 |
| 总检查/失败 | 182/3 | 185/0 | 182/3 |
| 执行状态 | exit1 | exit0 | exit1 |

覆盖缺失文件、信息/size/seek/read失败、追加/残行、替换/截断/截断再增长/volume、UTF-8跨读与64KB长行、256行批次。
测试中的真实分配失败以及info/read替身异常均保留传播；不宣称异常状态回滚或实机磁盘故障复现。
基线与回滚完整stdout一致，普通行及状态三态一致，编译exit0，stderr为空。
目录Query35项及客户端内置17/17、补全20/20、console/log17三态不变；Debug/Release通过。

初版AST只接受直接常量，未识别catalog的字符串 `.replace`表达式，脚本exit1；修正为读取该表达式的字面量而不执行它。
`fixture_ast_error.txt`保留失败来源。修正后基线仅剩三项实际资源残留失败。

## 记录

报告：`test/reports/20261014_tail_handles/`。
复用 `test/reports/20261012_variable64_transaction/`四角色：
`MODIFIED_FILE.zip`、`DIFF_FILE.patch`、`VERIFICATION.txt`、`ROLLBACK.sh`。
脚本对 `*.tail-handles.zip`、`*.tail-handles.exe`副本恢复本批基线；完整包另验证补丁重建/最初基线回滚。
新客户端未部署，插件DLL未变，实际GUI、并发pipe/线程及游戏环境不是本批新验收。
设计见[客户端共享句柄与日志读取](../../ai_docs/05_工具链/客户端共享句柄与日志读取.md)。
