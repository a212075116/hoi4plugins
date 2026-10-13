# 日志接口三态回归

2026-10-14，第十一批：共享 `Plugin_Log` 声明，保留实现与日志行为。

## Interface检查

从项目根执行：

```powershell
python test/modules/console/test_plugin_log_interface.py SOURCE_ROOT BASELINE_ROOT OUTPUT
```

输入根必须包含完整 `src/`，基线为本批修改前源码；输出使用独立目录。
基线和回滚阶段编译现有17条extern；修改阶段重复包含新增头文件，两者均以同一variadic函数指针类型检查。
同时检查单一实现、17个调用模块及底层日志原始字节。
精确文本guard只移除指定include/extern，不忽略函数体空白和字符串差异。
该测试不运行日志函数，生产日志行为由独立console/log夹具检查。

| 观察 | BASELINE | MODIFIED | ROLLBACK |
|---|---|---|---|
| 手写日志extern数量 | 17 | 0 | 17 |
| 独立接口类型编译 | exit 0 | exit 0 | exit 0 |
| 运行实现文本guard | 一致 | 一致 | 一致 |
| console/log行为 | 17/17 | 17/17 | 17/17 |
| Array64注册 | 4100/4100 | 4100/4100 | 4100/4100 |
| scalar64注册 | 27268组通过 | 27268组通过 | 27268组通过 |
| Bool/typed Trigger | 22/22、27/27 | 22/22、27/27 | 22/22、27/27 |
| 摄像机adapter | 13/13 | 13/13 | 13/13 |
| 成就资格/来源/UI包装器 | 31/31、16/16、12/12 | 31/31、16/16、12/12 | 31/31、16/16、12/12 |

相同输入的执行stdout、stderr和退出状态一致；接口编译另保留编译输出及声明数量变化。
scalar64保留完整输入与原始stdout文件及哈希。UI包装器仍含10000次更新，不是画面目视验收。
Debug/Release通过，源码ZIP及DLL副本经回滚后恢复本批基线字节；工作区保留修改版。

## 证据与边界

报告：`test/reports/20261014_plugin_log_interface/`。
包括基线哈希、三态夹具、`scope_guard.json`、构建输出、回滚和 `final_verification.json`。
首次工程筛选表修改假设了错误缩进，Python断言失败exit 1；已按实际XML行修正，仅补齐尚未完成的筛选表步骤。
`project_filter_error.json`保留错误来源及修正，不把它算作生产运行故障。

四角色继续复用 `test/reports/20261012_variable64_transaction/` 下的
`MODIFIED_FILE.zip`、`DIFF_FILE.patch`、`VERIFICATION.txt`、`ROLLBACK.sh`。
回滚脚本对 `*.plugin-log.zip`、`*.plugin-log.dll`独立副本恢复本批基线；完整包另验证binary patch重建与最初基线回滚。

没有部署、启动/重启游戏或执行Steam调用，不增加实机、多小时或多人验收声明。
接口职责见[日志接口与职责边界](../../ai_docs/03_插件/日志接口与职责边界.md)。
