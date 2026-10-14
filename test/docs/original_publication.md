# 原函数预发布三态回归

2026-10-14，第二十批。

## 命令

从项目根运行：

```powershell
python test/modules/hook/test_original_publication.py SOURCE_ROOT OUTPUT
```

源根完整src，MSVC x64，输出独立目录。
包含真实日期UI/单hook适配器，提取process与variable64安装函数；在模拟MH_EnableHook内立刻检查并进入回调。
覆盖十一个槽位、缺失module/readability、Create/AlreadyCreated/Enable/Init失败、旧original非NULL、ready标志和算术read mask。

| 观察 | BASELINE | MODIFIED | ROLLBACK |
|---|---|---|---|
| 配置/检查 | 1360/12170 | 同左 | 同左 |
| 发布断言失败 | 1839 | 0 | 1839 |
| 执行状态 | exit1 | exit0 | exit1 |
| 最终槽位/标志/native调用序列 | 旧行为 | 完全相同 | 完全相同 |

只剔除publication_wrong及callback_faults字段再比较每行，不丢弃最终状态或创建/启用/移除/重试记录。
基线与回滚完整stdout一致。日期回调以实际函数和SEH记录旧NULL故障，其余回调入口受控，不冒充整个业务被执行。

既有日期/UI、Array64/scalar注册、Bool/typed/摄像机/console三态回归保持。
当前scalar身份、存储、算术、语言桥接、ROOT作用数、setter债务、文本/名称字段/解码/debt生命周期回归通过。
日期/UI旧夹具补了新接口的受控适配器，保留原返回接口计数行为，不改原测试语料或期望。
Debug/Release及源码/DLL副本回滚通过，未部署/进入游戏。

## 记录

报告：`test/reports/20261014_original_publication/`，含三态、数值回归、scope guard、构建及最终验证。
复用 `test/reports/20261012_variable64_transaction/`四角色：
`MODIFIED_FILE.zip`、`DIFF_FILE.patch`、`VERIFICATION.txt`、`ROLLBACK.sh`。
脚本对 `*.original-publication.zip`或 `*.original-publication.dll`恢复本批基线，完整包另验证binary patch及最初基线回滚。
未证明所有并发/卸载安全、真实GUI或间歇退出根因，原验收取舍和完整项目goal保持不变。
设计见[预发布与数值绑定](../../ai_docs/03_插件/原函数预发布与数值Hook绑定.md)。
