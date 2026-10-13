# 日期增量算术三态回归

2026-10-14，第十四批：月份归一化、固定单位宽算术、raw解码及Effect转换边界。

## 运行

从项目根执行：

```powershell
python test/modules/gamedate/test_gamedate_arithmetic.py SOURCE_ROOT OUTPUT --optimization Od
python test/modules/gamedate/test_gamedate_arithmetic.py SOURCE_ROOT OUTPUT --optimization O2
```

两种模式使用独立输出目录。复用现有日期/UI夹具，提取生产 `RunAdd`，只替换原生依赖。
Python任意精度整数生成日历、目标raw、旧定义域标签及float32位模式oracle；不复制生产算法为期望值。
语料固定种子20261014，原始输入、编译/执行输出、优化模式和哈希均保存。

| 每种模式观察 | BASELINE | MODIFIED | ROLLBACK |
|---|---|---|---|
| 算术语料 | 12007 | 12007 | 12007 |
| 旧定义域兼容样本 | 11200、0失败 | 同左 | 同左 |
| 兼容状态/UI摘要 | 12457118709805104140 | 同左 | 同左 |
| Effect浮点语料 | 56 | 56 | 56 |
| 总断言/失败 | 239517/1303 | 239517/0 | 239517/1303 |
| 执行状态 | exit1 | exit0 | exit1 |

基线与回滚完整stdout一致；修改版两种模式stdout一致。编译均exit0，执行stderr空。
旧定义域标签要求中间乘加、月份加法和旧raw减基准均可表示，不把旧未定义行为混成兼容要求。
检查跨年/负月份/月末、年份夹紧、int极值、算术拒绝的状态/UI原子性、NaN/Inf/越界float、小数向零截断，以及tooltip flush/执行计数顺序。

另外，原有合法日期/UI夹具三态192637项零失败，读序摘要10827580189841091891不变。
Array64/scalar64/Bool/typed/摄像机/console回归三态不变；日期解析边界修改版重新通过。
Debug/Release、独立源码包/DLL回滚及完整包重建通过。

## 报告与范围

报告：`test/reports/20261014_gamedate_arithmetic/`，包括三态两种优化语料、一般回归、scope guard、微基准、构建、回滚和最终验证。
`benchmark.json`的 `/O2`单次微基准两版都亚毫秒、最终raw一致；不能推出实际游戏帧率或长期资源收益。
继续复用 `test/reports/20261012_variable64_transaction/`四角色：
`MODIFIED_FILE.zip`、`DIFF_FILE.patch`、`VERIFICATION.txt`、`ROLLBACK.sh`。
脚本对 `*.gamedate-arithmetic.zip`、`*.gamedate-arithmetic.dll`副本恢复本批基线；完整包另验证binary patch及最初基线回滚。

未部署、未进入游戏；实际UI、多人与任意低层EncodeParts输入不属于本批验收。
设计见[日期增量算术与浮点边界](../../ai_docs/03_插件/日期增量算术与浮点边界.md)。
