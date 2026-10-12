# Array64 变长意图日志与重启修复

2026-10-12，HOI4 1.19.3 Windows x64。已有形状事务之上增加独立操作意图日志，仍未注册脚本API。
源码array64_shape_journal.c，入口JournalPrepare、JournalBegin、JournalApply、JournalRecover、JournalFinish。
不修改原有ImportOwned的固定形状条件；专用恢复必须有本次事务的额外归属证明。

## 意图与原生事务标记

每次操作分配四个新的31位正整数nonce，原生标记__v64t_NAME_n0..n3及__v64t_NAME_p=1。
Begin在已持久化意图通过校验、当前基线仍精确匹配之后，才写原生标记；Apply仅接受标记全匹配的意图。
Prepare拒绝已有或残余事务标记，不覆盖未完成操作。
操作意图无指针，明确little-endian，magic A64JRN02、版本1。
120字节固定头包括op/index、原长度/世代、目标长度、raw/wide/size、lineage、八项分支/组归属、四项nonce、scope/name/内层字节数。
之后是scope/name、已有组的完整包装基线（create明确无原始组）、最后8字节FNV64。
所有长度、枚举、目标长度推导、scope/name/lineage、内外校验与原始编码分别验证；不能根据文件任意扩大清理范围。
校验和仍不是密码学认证，宿主/身份解析器必须可信；不接受任意外部文件作为写授权。

## 重启修复规则

JournalRecover先匹配存档中的四个nonce与p标记，再要求奇数gen=原gen+1。
每个仍存在的分支/组归属标记必须与意图一致；匹配事务证明下允许被本次clear删除的标记暂时缺失。
逐项扫描实际命名空间，拒绝超出本次原长度/目标长度范围的元素、非规范索引、额外标量/归属/事务后代键。
因此不是“缺槽就补”：没有标记、错scope、错nonce、外来归属或范围外键一律无写入拒绝。
已有组恢复全部原始三列与长度/归属，删除本次新增尾槽，发布新偶数gen；失败创建恢复为原始命名空间不存在。
恢复失败继续保持奇数且保留意图/标记，可显式重试；无法确认隔离标记则返回严重后端错误，不声称安全。
完成后清理五个事务标记。JournalFinish支持已验证提交、补偿和重启恢复后的清理与幂等核对。
Apply正常成功/即时补偿会清理标记；隔离失败保留标记供恢复，不把所有失败都转成0。
逻辑数据已正确而最后清理失败时仍必须报告，不能让下一次操作覆盖残余标记。

Prepare使用调用方分配的opaque Journal工作区，大小由JournalBytes查询，避免把约98KB快照放在游戏/Frida栈上。
捕获、解析与恢复都重新绑定当前容器，不在文件保留旧指针；仍限于稳定同步游戏线程。

## 五scope实际重启

本国、另一国、州、角色、global各六组，共30组。先Prepare并将30份意图文件flush/fsync、replace和重开，随后Begin/Apply。
在真实原生put/delete路径制造隔离，进一步真实删除槽/列长度/归属，保存新ajr存档后退出重启。

| 场景 | 观察结果 |
|---|---|
| create中断 | 5组清理专属数据、归属与事务标记，恢复为不存在 |
| resize中断且缺lo槽/列长度改变 | 5组补回原始两元素、长度和归属，gen4 |
| clear中断且缺hi槽/hi长度/归属 | 5组完整重建基线，gen4 |
| 恢复步骤失败后重试 | 5组先仍隔离，再恢复基线，gen4 |
| 使用另一scope的实际意图文件 | 5组无写入拒绝，仍隔离 |
| 当前incarnation标记被改 | 5组无写入拒绝，仍隔离 |

恢复后的已有组raw为[1234567890112500,-1]，同名scalar64仍12345678901.125、原版数组仍[2.5,7.75]。
记录重载后的545次原生写删；排除合法目标数据、归属及事务根后，容器其他键/raw集合保持不变。
恢复重放拒绝；已完成清理的Finish再次调用返回幂等结果且不重写数据。
最终291/291检查通过，包含30项独立Python意图/内层文件解析；write60个、reload30个样本，相关解析错误0、游戏存活。
核对新存档时间与命令内部ok=1，未把加载旧存档算通过。

## 原生夹具与失败记录

同一C源码经MSVC /W4、有界模拟表和写删适配器执行244/244断言通过；stderr为空、退出码0，编译无警告。
包括恢复各实际数据步骤的拒绝/重试、坏文件、错误scope/nonce、外来birth、超出意图范围的键、正常提交/补偿清理和32轮压力。
这与游戏重启证据分开，不称为OS崩溃或断电测试。

首次CModule大栈局部快照触发链接缺__chkstk，RPC samples未初始化；已改为调用方opaque工作区，不注入替代栈探测函数。
第二次探针直接把NativeCallback对象当JS函数调用，导致缺槽/foreign模拟没有执行；已改用NativeFunction调用该适配器并重新启动新阶段。
失败startup_error.json、native_v1_console.txt、native_final/FAILED_probe_comparison.json与控制台保留，未算通过。
驱动现在先检查样本RPC初始化，再执行fixture事件，避免启动错误被命令成功掩盖。

## 使用入口与下一步

主证据test/reports/20261012_variable64_transaction/array_journal/native_fixed。
复现：工程根 `python test/modules/effect/verify_array64_journal.py NEW_PHASE`，会创建独立fixture、意图记录、新存档并重启。
核对：`python test/modules/effect/verify_array64_journal.py native_fixed --verify-only`。
夹具：`python test/modules/effect/test_array64_journal_native.py OUTPUT_DIR`。
新意图通路只修复已证明属于这次操作的固定授权范围，不用于未知存档迁移或任意损坏数据的自动修复。
本轮正常重启与逻辑故障拒绝不是游戏存档/侧车联合原子提交，也不是多人一致性证明。
创建前不存在的基线与已存在组分别记录；身份/分支转换仍由可信控制器明确管理，不声称自动发现所有手工存档复制。
下一步进入生产构建和effect/trigger脚本接口接入，参数与scope校验、工具提示和恢复错误必须明确，再执行完整验收。
现有索引set_variable64保护继续保留；不要把诊断CModule已通过误报为作者已经能使用公开Array64语法。
