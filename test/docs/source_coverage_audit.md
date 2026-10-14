# 源码覆盖核对与公开头依赖

2026-10-14，第二十六批；本轮是跨模块审计和一项已证明多余依赖的修正，不是全目标完成声明。

历史范围：本篇保留发现缺口时的旧状态；F2已由[第二十七批](iat_install.md)、F3由[第二十八批](bootstrap_registration.md)收口所列合同；F1原生所有权仍未知，现按[收尾核对](normalization_closure.md)保留原实现及独立调查，不冒充已修复。

## 可执行检查

```powershell
python test/tools/audit_source_contracts.py SOURCE_ROOT OUTPUT
python test/modules/effect/test_var64_public_header.py SOURCE_ROOT OUTPUT
```

结构审计覆盖74份自有源码、3个自有项目，10个私有实现片段均有唯一编译根，quoted include无未解析项。
首次扫描连第三方MinHook的vcxproj也计入而显示19；已明确排除第三方项目并重跑为3，不把计数当作语义验收。
selected模块合同、原始hash、包含图、编译归属及F1/F2/F3源码锚点保存在result.json。

## 公开头同输入三态

把实际variable64.h复制到隔离目录，不提供项目include路径；同一probe核对slot常量、声明类型和x64指针宽度。

| 编译 | BASELINE | MODIFIED | ROLLBACK |
|---|---:|---:|---:|
| C exit | 2，C1083 | 0 | 2，C1083 |
| C++ exit | 2，C1083 | 0 | 2，C1083 |
| probe输入hash | 同一 | 同一 | 同一 |

旧头需要无关effect_reg.h，所以“仅复制公开头”的测试失败；不是说原项目此前不能构建。
恢复头字节/hash一致，C1083内容一致但诊断中的绝对输出目录不同；原始stdout分别保留，不宣称字节完全一致。
首次比较误要求完整stdout相同，AssertionError exit1已记录；随后仅替换各自cwd进行对照，不重跑已经完成的编译。
不把独立语法编译当作C++链接、DLL导出ABI或游戏实现测试。

## 复用与新验证

源码只删一条多余include；所有实现函数、其他源码、常量和声明保持字节一致。
既有实机、标量/Array64/日期、allocator/string政策及第21至25批启动/异步I/O证据按范围复用，不把旧用户GUI验收重记为本轮验证；完整源码hash不同的旧报告不能自动支持当前全部代码。
本轮console17三态及Release/Debug构建通过；独立CHI修改版/恢复版各验证就绪和大数→原版2.5语义，最终重新应用修改版。
PID、真实加载路径、hash和原始命令以报告为准；40既有存档hash再次核对。
文档三态采用同一audit_project_docs.py --package输入形式，恢复项目副本由ROLLBACK.sh执行，不修改原始存档或原始备份。

## 不能宣告完成的原因

F1是需要证明的临时字符串所有权，不是测得的真实泄漏；F2/F3是源码可见的错误结果/完成汇总缺口，尚需对应故障执行证据。
结构清单覆盖74份文件，不意味着每个函数已语义认证；通过现有测试不能消除这些未覆盖项。
GUI/真人多人、排除的掉电和暂缓的间歇退出按用户原取舍保留，不制造新阻塞项。

报告 `test/reports/20261014_source_coverage/`。
继续复用 `test/reports/20261012_variable64_transaction/` 四角色：
`MODIFIED_FILE.zip`、`DIFF_FILE.patch`、`VERIFICATION.txt`、`ROLLBACK.sh`。
本批回滚后缀`*.coverage-source.zip`、`*.coverage-source.dll`、`*.coverage-project.zip`对应源码/build/含文档项目基线。
维护入口见[模块边界与所有权](../../ai_docs/01_工程与构建/模块边界与所有权.md)。
