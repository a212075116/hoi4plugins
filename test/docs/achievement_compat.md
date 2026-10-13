# 成就模块：阶段进展与历史测试

2026-10-13。**当前已启用单人资格兼容，并完成ID254的真实解锁确认。下文基础模型与三态属于历史第一阶段，不代替当前实机验收。**

## 查看状态

游戏进入地图后在外部控制台执行：

```text
achievementstatus
achstatus
```

输出铁人位、定义与各候选列表数量、manager原始A0..A4及调试标志。
返回成功代表读取成功，不代表所有成就可解锁；旧消息含`compatibility hooks NOT enabled`，当前使用`compatibility_installed`字段。
只支持已验证1.19.3 PE指纹；不支持或游戏未就绪时不读取状态，不调用任何成就修改接口。

## 策略模型

```powershell
python test/modules/achievement/run_policy_matrix.py MODIFIED
```

512组合包含模式、会话、单人、平台、其他possible、铁人、资格checksum、happened、已解锁。
其他possible不成立、未达成、已解锁、多人或平台未就绪均不产生提交决策。
这是纯模型，不是对原版函数Hook或账号解锁的测试。

| 三态 | 策略参考模型 | 原生探针命令 |
|---|---|---|
| BASELINE | 509/512，exit1 | Unknown command，exit1 |
| MODIFIED | 512/512，exit0 | 只读读取成功，exit0 |
| ROLLBACK | 509/512，exit1 | Unknown command，exit1 |

100次原生读取成功，manager168字节前后SHA256相同；未调用SetAchievement、StoreStats、ClearAchievement或ResetAllStats。
历史第一阶段真实铁人位为1、定义数为0，原因是测试mod的0字节覆盖；这不是当前CHI测试局。
资格未实现时的非铁人CHI现场曾为定义293、候选0，吞并并推进一月仍未解锁。
原版来源新命令为`achievementsource`/`achsource`，读取Hook/挂载/加载/重定向/失败计数。
真实来源读取已出现loads=1、redirects=1、failures=0；来源检查本身不等于解锁验收。
用户允许真实条件达成后的账号解锁，不使用成就清除/重置回滚。
详见[原版来源测试](achievement_original_source.md)、[CHI端到端流程](achievement_chi_annex_flow.md)。

证据与基线位于`test/reports/20261013_achievement_compat/`。
当前真实解锁、负对照与保存恢复结果见[资格兼容测试](achievement_eligibility.md)；更多平台/模式覆盖待扩展。
账号成就不作为文件回滚的一部分，ID254不清除或重置。
相关：[资格链路与进展](../../ai_docs/11_成就系统/资格链路与阶段进展.md)、[当前项目状态](../../ai_docs/09_脚本数值系统/当前状态与复现.md)。
