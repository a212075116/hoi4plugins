# 启动注册汇总三态

2026-10-14，第二十八批，覆盖审计F3。

## 入口

```powershell
python test/modules/console/test_bootstrap.py SOURCE_ROOT OUTPUT
python test/modules/effect/test_var64_hook_retry.py SOURCE_ROOT OUTPUT
```

第一项直接复制旧PluginThread的两个注册块，或新RegisterPluginGroups/poller/步骤表；外部registrar、ready和Sleep受控。
521输入覆盖512暂态组合、8永久注册组失败及永久scalar hook readiness失败，确认完成组跳过、其他组不饥饿、超时如实报告。
第二项直接编译实际算术hook安装器/新ready查询，控制64安装失败×64不可读组合，清除故障后重试并重复调用。

| 启动汇总 | BASELINE | MODIFIED | ROLLBACK |
|---|---:|---:|---:|
| 输入 | 521 | 521 | 521 |
| 检查 | 8877 | 39942 | 8877 |
| 新合同失败 | 2577 | 0 | 2577 |
| exit | 1 | 0 | 1 |

| hook重试 | BASELINE | MODIFIED | ROLLBACK |
|---|---:|---:|---:|
| 输入/检查 | 4096/32768 | 同左 | 同左 |
| 失败 | 13607 | 0 | 13607 |
| exit | 1 | 0 | 1 |

两项输入hash一致；恢复完整stdout与基线一致，源包/DLL恢复hash一致。
执行分支变化使启动检查数不同，不宣称修改版全部stdout相同。

## 回归、实机和错误记录

标量27268、Array注册4100、日期192637、Bool22/typed27、摄像机13、console17三态执行；Release/Debug构建通过。
计数从模块头声明后，注册夹具需包含相应实际头；Array夹具最初缺macro编译exit2，保留错误再修正，不为夹具更改生产语义。
一次检查引用不存在的旧registration_glue路径，已改用实际test_array64_registration.py；旧路径错误留存。
真实CHI新日志逐项核对8组result=expected且complete=1，区别于仅看achsource/transport成功。
修改版/恢复版均测试大数→原版2.5；最终重新部署修改版，不用Frida spawn或倒计时kill，不覆盖正式存档。
正常路径注册器可自行保存成功entry；本批不会free未知map对象，不把原生外部API受控依赖当作全面allocator故障证明。

## 归档

报告 `test/reports/20261014_bootstrap/`包含原始结果、输入hash、scopeguard、错误、组日志及当前部署。
继续复用 `test/reports/20261012_variable64_transaction/`四角色：
`MODIFIED_FILE.zip`、`DIFF_FILE.patch`、`VERIFICATION.txt`、`ROLLBACK.sh`。
本批副本后缀`*.bootstrap.zip`和`*.bootstrap.dll`恢复本批原始字节。
设计见[注册组完成与分阶段启动](../../ai_docs/01_工程与构建/注册组完成与分阶段启动.md)。
