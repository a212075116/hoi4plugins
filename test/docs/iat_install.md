# IAT安装结果、保护与重试三态

2026-10-14，第二十七批，覆盖审计F2。

## 入口

```powershell
python test/modules/console/test_iat_install.py SOURCE_ROOT OUTPUT
python test/modules/console/test_iat_install.py SOURCE_ROOT OUTPUT --real
python test/modules/hook/verify_iat_install.py PID OUTPUT_JSON
```

前两项提取实际安装/槽位策略及RedirectA；导入查找和回调主体受控。真实模式使用真实只读共享页、VirtualProtect/CAS/SRW和线程，不冒充实际游戏PE遍历。
第三项只读附加当前进程枚举导入槽位，没有hook、native调用、spawn或kill；确认目标落在插件模块，不鉴定精确私有符号。

## 同输入故障三态

| 实际策略矩阵 | BASELINE | MODIFIED | ROLLBACK |
|---|---:|---:|---:|
| 场景 | 4100 | 4100 | 4100 |
| 检查 | 61637 | 96114 | 61637 |
| 新合同断言失败 | 7219 | 0 | 7219 |
| exit | 1 | 0 | 1 |

输入hash一致；分支不同导致检查数不同。恢复版完整stdout与基线相同，源码/DLL恢复hash相同。
矩阵涵盖16种缺失、16种写失败、16种恢复失败及CAS竞争、首次foreign、未知self、NULL原函数。
验证失败后安全callthrough、未完成gate不重定向、保护恢复先于继续同页安装、重试不自捕获和用户enabled独立。

## 真实内存与实机

三态正常路径均在真实RO共享页运行32线程×64次安装/检查/callthrough；新版14450检查、0失败，保护回到RO，拥有的线程句柄数恢复。
console17回归三态、Release/Debug构建通过。
独立CHI修改版/恢复版分别确认IAT模块归属、就绪和大数→原版2.5；最终修改版再次应用。
正常关闭等待进程结束后才部署，不用倒计时kill，不保存正式局；既有40存档hash再次核对。

## 留存错误与限制

初次函数提取器只支持static，公共FileRedirect_Install触发ValueError exit1；只在夹具提取文本补static，生产签名未改。
初版将InterlockedCompareExchangePointer用于只读IAT快照，夹具11153断言失败、exit1；改为volatile读，CAS只在成功RW保护后执行。错误版本没有部署。
原测试PID在候选部署前已结束，旧正常关闭驱动报exit1；句柄Wait返回终态后才继续新开独立CHI，不推测退出原因，不转入已暂缓调查。
恢复版关闭请求返回False后，同一进程句柄已终态，故只续做最后重应用步骤。一次最终快照之后进程也结束，模块查询空输出触发JSONDecodeError exit1；再次确认终态后用无Frida的独立启动核对当前部署，已有快照/语义结果不重计为新测试。
callback主体和PE遍历没有由故障夹具直接执行；实际源码保持字节不变，模块范围只读实测另列。
部分安装不是卸载；不保证协调所有foreign模块保护竞争，也不保证cached状态检测检查后任意改写。
F3和F1仍为下一批工作，F1不能未证明所有权就free。

## 归档

`test/reports/20261014_iat_install/`保存命令、literal stdout/stderr、exit、scopeguard、失败修正、真实内存和实机快照。
继续复用`test/reports/20261012_variable64_transaction/`四角色：
`MODIFIED_FILE.zip`、`DIFF_FILE.patch`、`VERIFICATION.txt`、`ROLLBACK.sh`。
本批副本后缀`*.iat-policy.zip`、`*.iat-policy.dll`恢复本批基线。
设计见[IAT安装状态与安全重试](../../ai_docs/01_工程与构建/IAT安装状态与安全重试.md)。
