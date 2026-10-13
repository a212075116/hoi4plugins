# 日期/UI三态重构回归

2026-10-14，第十二批：删除文本设置路径的重复编码，清理公开接口及UI依赖。

## 可复现入口

从项目根目录执行：

```powershell
python test/modules/gamedate/test_gamedate_refactor.py SOURCE_ROOT OUTPUT
```

源根包含完整 `src/`，输出使用独立目录；需要MSVC x64工具链。
夹具直接包含生产 `gamedate.c`和 `gamedate_ui.c`，替换模块基址、内存检测、hook安装、UI函数和命令注册依赖。
不调用游戏、Steam或真实hook。oracle独立计算固定365天日期编码和月份归一化，随机种子固定为0x20261014。

| 相同输入/观察 | BASELINE | MODIFIED | ROLLBACK |
|---|---|---|---|
| 日期/加时间/参数矩阵 | 20000/4000/140组 | 同左 | 同左 |
| 断言与失败 | 192637项、0失败 | 同左 | 同左 |
| UI回调/主动刷新 | 28009/28004 | 同左 | 同左 |
| 内存检测次数 | 208304 | 同左 | 同左 |
| 执行退出状态 | 0 | 0 | 0 |
| 独立公开头文件，无console搜索路径 | C1083、exit2 | exit0 | C1083、exit2 |

主夹具的stdout、stderr及退出状态三态一致，内存检查顺序摘要均为10827580189841091891。
覆盖：缺失模块、安装失败后重试、重复初始化、panel捕获/丢弃、原回调缺失、刷新与内存失败、派生字段、月份边界、null输出、SSO/外部参数、size/dst长度及写入canary。
UI回调在写日期时立即调用；这不是实际暂停画面或渲染验收。
独立头文件是有意改善的依赖行为，编译状态2→0→2单独记录，不与主夹具执行状态混淆。

其他三态回归：Array64注册4100、scalar64注册27268、Bool22、typed27、摄像机13、console/log17，执行输出一致。
Debug/Release通过；源码ZIP、DLL副本回滚后恢复本批基线哈希，工作区保留修改版。

## 新发现的边界问题

`overflow_finding.json`记录独立 `/O2`探针：修改前、修改后均接受 `4294969232.1.1`，并解码为1936.1.1。
这是第十二批发现的整数解析问题，不算合法输入回归中的“通过”，第十二批没有修复；当前见[第十三批边界修正](gamedate_parser.md)。
主夹具未将超长整数和任意int极值归入合法日期oracle；第十三批已追加拒绝、溢出和null参数测试，详见上述新记录。

## 归档

报告目录：`test/reports/20261014_gamedate_refactor/`，包含基线、三态夹具、独立头文件、溢出探针、scope guard、构建和最终验证。
持续复用 `test/reports/20261012_variable64_transaction/` 下的四角色：
`MODIFIED_FILE.zip`、`DIFF_FILE.patch`、`VERIFICATION.txt`、`ROLLBACK.sh`。
回滚脚本接受 `*.gamedate-refactor.zip`或 `*.gamedate-refactor.dll`副本，恢复本批基线；完整包另验证binary patch重建及最初基线回滚。

没有部署或启动游戏；用户已授权需要时通过 `-start_tag=TAG`自动开局，实机验收另行记录。
设计与保留策略见[日期编码复用与界面依赖](../../ai_docs/03_插件/日期编码复用与界面依赖.md)。
