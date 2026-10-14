# 规范化实机三态与载体日志回归

2026-10-14，第二十一批。

## 可复现入口

```powershell
python test/modules/carrier/test_carrier_logging.py SOURCE_ROOT OUTPUT
python test/tools/run_normalization_smoke.py --pid GAME_PID --helper CLIENT_EXE --report PHASE_DIR
```

载体夹具直接测试真实PLog/公共后端，受控文件及时间；25场景93检查三态stdout/stderr/exit相同，exit0。
live工具只向已启动明确PID发送命令，不部署、启动、保存或终止游戏；首次执行必须独立测试局，report不能混用另一PID。
包含日期重设、Array64新建等写操作，不能对正式存档或已执行同名array的局重复整组；工具保留已完成命令并只续未执行项。
游戏启动/阶段关闭/版本恢复由本轮明确控制步骤记录，无超时杀游戏。

## 实机观察

| 阶段 | PID | 命令 | 语义检查 |
|---|---:|---:|---|
| BASELINE原部署 | 56136 | 19 | 11/11 |
| MODIFIED当前Release | 51936 | 19 | 11/11 |
| ROLLBACK原部署 | 5032 | 19 | 11/11 |
| 最终重新部署修改版 | 53864 | 来源就绪查询 | definitions293 |

native基线为第二十批后的源码/build，live基线为原来部署版本，两者分别保存，不混淆哈希或回滚时间点。
live内容/状态见各命令literal输出、日志、comparison及实际loaded module路径；只比较规定语义，不比较pid/thread/随机lineage等字段。
补全9个set_名称、日期1936.2.1.11、scalar12345678903.625、vanilla值2.5、Array645000000000.125/count3和两个Result=yes均观察到。
修改版超长年份拒绝和写入失败原子性另保存boundary_check。
既有40份保存文件修改部署前/最终后哈希一致，未发savegame或continue命令。

## 错误与保留记录

最初effect命令是scripted effect名接口；改为eval_effect后执行真实内联代码。
最初check_variable64不是本项目实际trigger；改为plugin_check_variable64，失败记录 `syntax_error_wrong_trigger.json`保留。
trigger输出是Result=yes而非true，已修验证器；不伪造代码失败。
未标记变量log_variable64显示1，而真实语言值2.5；比较以语言/回收标记证明setter结果，诊断差异在三态原始输出中保留待审。
exit命令未知、quit补全为空后改为明确CloseMainWindow；没有到期kill；实际退出后才覆盖DLL。

## 归档和验收边界

报告：`test/reports/20261014_closure_integration/`，含前后部署/加载路径、native/live三态、save哈希、控制命令及最终验证。
继续复用 `test/reports/20261012_variable64_transaction/`下的四角色。
`ROLLBACK.sh`对 `*.closure-native.zip`及 `*.closure-native.dll`恢复本批原始源码/载体build；live回滚是三个原部署文件的精确恢复，两种关系单列。
公共console/log17回归与Debug/Release通过；最终已部署修改版，CURRENT_BUILD同步，不再称“只归档未部署”。
GUI/真人多人、长时间/掉电取舍及间歇退出调查沿用现有用户要求；本smoke不证明这些，也不表示整项目source审查已自动结束。
设计与未完成项见[实机三态与载体收口](../../ai_docs/01_工程与构建/规范化实机三态与载体收口.md)。
