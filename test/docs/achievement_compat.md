# 成就模块：第一阶段测试

2026-10-13。**只读探针已部署，实际资格放行和Steam解锁未启用。**

## 查看状态

游戏进入地图后在外部控制台执行：

```text
achievementstatus
achstatus
```

输出铁人位、定义与各候选列表数量、manager原始A0..A4及调试标志。
返回成功代表读取成功，不代表成就可解锁；消息明确含`compatibility hooks NOT enabled`。
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
本次真实铁人位为1，原版定义数为0；实际mod用0字节`common/achievements.txt`覆盖原版，这不是“已达成仍不解锁”的实机验收。

证据与基线位于`test/reports/20261013_achievement_compat/`。
真正放行后的未达成/达成/重复/重载/平台未就绪及Steam回调仍待后续验证；账号成就不作为文件回滚的一部分。
相关：[资格链路与进展](../../ai_docs/11_成就系统/资格链路与阶段进展.md)、[当前项目状态](../../ai_docs/09_脚本数值系统/当前状态与复现.md)。
