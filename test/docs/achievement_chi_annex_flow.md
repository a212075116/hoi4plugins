# CHI 吞并全部国家：端到端成就验收

2026-10-13。用户指定流程：选择 CHI → 吞并全部国家 → 推进一个游戏月。

## 当前执行结果

用户报告已完成上述流程，没有解锁成就。
资格未实现时的旧版本仍是只读探针，用户初测未解锁。旧现场读取：ironman=0、definitions=293、pending=0、completed=0、excluded=0；
A0..A4=0,1,0,0,0；debug 与 debug_or_crash_log 均为 1。
这说明旧现场定义已经加载，但候选列表为空；不能用等待一个月替代资格初始化。
不能把模型矩阵或只读命令成功当作此流程验收成功。
当前资格版本已完成CHI吞并→正常推进744小时：ID254从pending变completed，用户确认Steam解锁提示。
ID255/256仍pending；详情与恢复证据见[资格兼容测试](achievement_eligibility.md)。

## 必须保留的边界

- 单人专用测试局，不使用正式战役存档；保留原始存档与操作前副本。
- 原版定义始终来自游戏根目录 common/achievements.txt，忽略 mod 的公开同名文件覆盖。
- 不设置或伪造真实 happened 所需旗标，不把所有触发器改成真。
- 不使用直接 Steam 赠送、清除或重置接口；账号成就不能随文件回滚。
- 暂停启用已定位存在旧师团界面覆盖的 politicalxxx mod，避免混入入图崩溃。
- 吞并指令的确切拼写、起始日期、难度、DLC、mod、游戏规则和 Steam 已解锁状态需随案例记录。
- 本次原始吞并指令拼写尚未知，不将它擅自记作某个具体命令。

## 顺序与检查点

1. 新建单人、非铁人 CHI 测试局，记录真实起始条件；入图后捕获 before。
2. 先验证定义加载与候选初始化。兼容功能未启用、定义为零或候选异常时，不进入解锁成功判定。
3. 使用用户原来的吞并全部国家流程，记录字面命令；捕获 after-annex。
4. 从吞并完成时推进一个游戏月，记录前后日期；捕获 after-month。
5. 核对具体目标成就的 possible 与 happened 原生结果、是否已解锁、平台状态与原版提交回调。
6. 保存后重载确认；已解锁目标不可用来证明首次解锁。不得通过清除账号成就恢复测试基线。

## 具体目标：不得把“吞并”当作全部条件成立

以本机原版定义为准，以下仅为候选与负对照，并非本局已满足证明：

| 定义名 / ID | 原版真实条件的关键部分 | 在此流程中的作用 |
|---|---|---|
| genghis_khant / 264 | 允许 CHI；拥有并控制蒙古全部核心州 | 优先正向候选，需核对核心州控制与已解锁状态 |
| awake_and_angry / 55 | 对日议和完成旗标，以及有关核心州归属 | 未发生议和事件时的负对照，吞并不能代替旗标 |
| romance_of_the_three_kingdoms / 56 | GXC 和 YUN 对应的两个成就旗标 | 没有旗标时保持不解锁 |
| the_coast_is_clear / 255 | 日期晚于 1945.9.2，且未丢失沿海州旗标 | 1936 起局推进一个月仍不满足日期 |
| a_fullmetal_brotherhood / 256 | 法西斯政体，钢/钨/铬各实际开采超过 299 | 吞并本身不改变政体，不保证条件成立 |

其他难度、开始日期等 possible 条件按项目已确认边界保留，不因吞并而忽略。

## 只读采集脚本

在项目根目录执行；PID 取当前游戏 PID，不复用历史 PID。

```powershell
python test/modules/achievement/capture_chi_flow.py --pid PID --phase before --case test/reports/achievement_chi_flow/CASE
python test/modules/achievement/capture_chi_flow.py --pid PID --phase after-annex --case test/reports/achievement_chi_flow/CASE
python test/modules/achievement/capture_chi_flow.py --pid PID --phase after-month --case test/reports/achievement_chi_flow/CASE
```

脚本只发送 achievementstatus；不吞并、不推进时间、不修改存档或 Steam。
保存字面 stdout/stderr、命令退出码、DLL/原版定义哈希、采集时间与阶段。
脚本 exit1 表示采集失败，exit2 表示明确仍未启用兼容功能，exit0 只表示采集成功且未看到禁用提示。
未来探针输出必须继续报告启用状态；没有禁用提示本身不构成启用或解锁证据。

## 完成标准

本流程的ID254单例已通过原生条件、候选链路、完成调用与用户平台确认。
未满足条件的ID255/256保持不解锁；不等于293项全量通过。
既有三态：探针 Unknown/只读成功/Unknown（exit1/0/1），模型509/512→512/512→509/512。
以上历史结果不替代本流程。
