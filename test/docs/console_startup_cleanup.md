# 外部控制台启动清理回归

2026-10-14，第二十三批。

## 可运行入口

```powershell
python test/modules/console/test_service_scheduler.py SOURCE_ROOT OUTPUT
```

在MSVC x64环境直接编译实际启动函数和hook adapter；资源API受控，不创建真正的游戏 Peer。
同一62场景覆盖旧25场景及每个 pipe/完成事件的失败前缀，各7641检查。

| 结果 | BASELINE | MODIFIED | ROLLBACK |
|---|---|---|---|
| 测试退出状态 | 0 | 0 | 0 |
| 检查失败 | 0 | 0 | 0 |
| 资源集合、其余操作和状态 | 基准 | 一致 | 一致 |
| 完整stdout | 基准 | 部分关闭顺序不同 | 与基线相同 |

不能把删除关闭事件后的轨迹比较描述为完整stdout相同。
源码只修改启动清理；Peer、Execute、Frame、协议、权限及hook发布字节未修改。
独立副本执行 ROLLBACK.sh 恢复源码包/DLL，哈希与基线相同，再运行同一夹具。
原有console17回归三态通过，Release/Debug构建通过。

## 真实游戏与残留问题

使用独立 `-start_tag=CHI` 游戏，不覆盖正式存档；重启只请求正常关闭，不用Frida spawn或倒计时kill。
实际PID、启动参数、就绪请求和语义日志保存在报告目录，不凭transport成功判断变量设置完成。
上批异常的独立离散复测得到12345678901.125及2.5，仅证明这次正常，旧失败证据保留。

所有Peer线程创建失败仍返回ready，是本轮夹具保留并明确记录的旧行为，需要后续修正；不是故障验收通过。
本清理函数只在Peer启动前使用，不是并发线程终止方案。

## 证据与四角色

报告目录 `test/reports/20261014_service_cleanup/` 保存原始结果、命令、stdout/stderr、退出码、资源轨迹、源码/DLL与哈希。
仍复用 `test/reports/20261012_variable64_transaction/` 的四角色：
`MODIFIED_FILE.zip`、`DIFF_FILE.patch`、`VERIFICATION.txt`、`ROLLBACK.sh`。
本批回滚后缀为 `*.service-cleanup.zip` 和 `*.service-cleanup.dll`，恢复的是本批原始字节。

设计见[启动资源清理](../../ai_docs/05_工具链/启动资源清理.md)。
