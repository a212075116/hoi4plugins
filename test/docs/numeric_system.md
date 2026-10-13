# 数值系统与Trigger测试入口

核对2026-10-12；以下命令从hoi4plugins项目根执行。只列现有脚本，不把历史通过数冒充本次重跑。
游戏驱动可能终止当前游戏、写测试mod/本地化并更新lastsave；先保存自己的进度。静态原生夹具不启动游戏。

## 当前使用与证据

- 当前功能/限制：[数值状态](../../ai_docs/09_脚本数值系统/当前状态与复现.md)。
- 对模组作者的语法、侧车备份：[Array64单人交付](../../ai_docs/09_脚本数值系统/Array64单人交付说明.md)。
- 最新配对检查点为a64soak与api/crash_soak_v4/soak_paired_sidecars/，不是旧recovery_v3/lifecycle_v1的原始generation。
- 当前资源增长尚未归因；先做等调用数对照，不把--soak-only长时运行当已验证命令结果。

## 可从新fixture开始的游戏驱动

| 命令/脚本 | 前提与动作 |
|---|---|
| `python -u test/modules/effect/verify_array64_api.py NEW_PHASE` | 先构建正确DLL；脚本部署、建立新对局/fixture、操作并保存重启 |
| `python -u test/modules/effect/verify_array64_api_recovery.py NEW_PHASE` | 新fixture，异常侧车/模拟中断/压力与重启；旧phase拒绝覆盖 |
| `python -u test/modules/effect/stress_variable64.py NEW_PHASE --extended` | scalar64固定种子扩展压力；部署/重启与存档会改变测试环境 |
| `python -u test/modules/effect/verify_setter_ownership.py NEW_PHASE --deploy --lifecycle` | 最后setter规则与存档；--attach只用于已加载其fixture的对局 |
| `python -u test/modules/trigger/verify_trigger_registry.py NEW_PHASE` | Bool注册器fixture；--stress是测试开关，必须各端一致并在结束后恢复 |
| `python -u test/modules/trigger/verify_typed_triggers.py NEW_PHASE --deploy` | 数值/比较块fixture，参数与scope验证 |

输出位置、命令内部ok、新存档时间/标记、相关解析错误及comparison.json均需核对；Python退出0不能代替这些证据。

## 依赖特定旧检查点的历史/阶段驱动

`test/modules/effect/verify_array64_api_lifecycle.py NEW_PHASE`复用recovery_v3/sidecar_index.json及相同容器、generation和prf侧车。
当前a64soak已推进generation，不能直接重跑；先还原那轮精确fixture存档/侧车，或明确重建并更新输入，不能随意拿当前文件替代。
`test/modules/effect/verify_array64_api_crash_soak.py NEW_PHASE --seconds 180`完整中断矩阵的国家基线generation=6，要求五scope健康prf及原配对。
扩展持续操作用--soak-only，不重复三个已完成中断门；使用新的精确a64soak配对备份并核对健康基线。尚未因此获得多小时/资源验收通过。
脚本的--verify-only只复核保存日志/期望；其中alive/DLL检查可能仍读取本机当前游戏和DLL，不是完全离线验收。
历史Array64 CModule阶段驱动仍保留，但不是正式接口推荐用法；finalize_*是阶段封包脚本，不是可随意运行的游戏回归。

## 原生夹具（受控依赖，不等于游戏/GUI）

2026-10-13数值源码整理的三态行为证据见[文本/侧槽命名回归](var64_refactor.md)、[名称字段/桥接回归](var64_name_fields.md)、[算术/解码回归](var64_math_refactor.md)、[债务生命周期回归](var64_debt_lifecycle.md)及[遗留/注册回归](var64_cleanup.md)；旧功能通过数与本轮实际重跑已分开记录。

```powershell
python test/modules/effect/test_array64_group_native.py OUTPUT_DIR
python test/modules/effect/test_array64_journal_native.py OUTPUT_DIR
python test/modules/effect/test_var64_identity.py src/plugin/SDK_RVA/variable64/variable64.c OUTPUT_DIR
python test/modules/effect/test_var64_raw_math.py src/plugin/SDK_RVA/variable64/variable64.c OUTPUT_DIR
python test/modules/trigger/test_trigger_registry_native.py OUTPUT_DIR
python test/modules/trigger/test_typed_trigger_native.py OUTPUT_DIR
python test/modules/trigger/test_typed_tooltip_native.py src/plugin/SDK_RVA/trigger/trigger_reg.c OUTPUT_DIR
```

依赖现有VS x64编译环境；OUTPUT_DIR使用全新目录并保留stdout/stderr/退出码、扩展源码哈希。
`test/modules/trigger/verify_array64_api_tooltips.py PHASE`会附加已就绪游戏并触发接口fixture、写本地化；只验证原生字符串/ABI，不是悬停视觉。

## 文档与包审计（不操作游戏）

```powershell
python test/tools/audit_project_docs.py --output docs_audit.json
```

检查行数、代码围栏、本地文档链接、已公布CLI路径及选定现状合约。外部URL与全部RVA语义不由该脚本自动认证。
reconcile_project_docs.py是一次性文档迁移记录，已完成的拆分不应重复执行；正常维护只使用审计器。
