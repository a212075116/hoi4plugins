# Array64 创建、变长与原生删除事务

2026-10-12，HOI4 1.19.3 Windows x64。承接归属门控；仍为诊断CModule，未注册公开脚本API。
array64_shape_transaction.c新增Array64_ShapeApply，工作区由Array64_ShapeBytes给出opaque大小。
这不是在固定长度setter上假装插入；真实创建/删除原生变量键，并处理整组三列形状变化。

## 原生新增与删除证据

新增/改值：0xBC5C10(container,{名字指针,长度},初始raw)，返回值槽；每次重新获取，允许原版扩容/回移。
删除：0x350240 clear_variable exec →0x5431D0 scoped clear →0xBC8FC0(container,名称视图)。
IDA反编译对0xBC8FC0漏标了第二参数，已用反汇编确认mov r8,rdx再调用只读查找；不能按错误单参数原型调用。
0xBC8FC0会释放字符串、回移后续Robin Hood节点并减少元素数，不是把raw写0或手工涂掉occupancy。
原始反编译与反汇编保存在array_shape/clear_exec_retry.json、clear_scoped.json、erase_native.json、erase_disasm.json。
旧IDA worker不可达的错误保留在clear_exec.json；使用技能open.ps1重新开库后查询成功。
适配器每次查找后验证实际raw或不存在，不跨新增/删除缓存节点地址。

## 操作语义

| op | 操作 | 语义 |
|---|---|---|
| 0 | create | 仅全部专属数据/归属根均空闲时创建，生成调用方提供的新归属；支持显式空组 |
| 1 | append | 末尾追加一个native/64编码元素 |
| 2 | insert | index范围0..len，三列同步右移 |
| 3 | erase | index范围0..len-1，三列同步左移并真实删除尾槽 |
| 4 | clear | 删除整个专属清单、三列和归属标记；不清同名原版标量/数组 |
| 5 | resize | grow用指定编码值填充，shrink真实删除尾槽；size=0保留有效空组 |

名称与数值沿用v2，native输入遵守此前安全保存范围，目标长度0..4096，世代禁止回绕。
create还检查远端残余元素及归属标量的^后代；不能因^num不存在就覆盖孤立键。
已有组要求完整合法、期望世代匹配且归属标记有效；索引不合法或已隔离组在写前拒绝。
创建的新incarnation由可信调用方提供，公开接口接入时必须由管理者生成，不能允许脚本随意复用旧身份。

## 事务与补偿

已有组捕获全组三列、长度、世代与八个归属分量，暂存目标形状；创建明确记录原始专属命名空间不存在。
先写奇数gen，再逐项安装归属、列、长度与清单，删除不再需要的原生键，最后发布新偶数或完成clear删除gen。
写/删均有确认；任何阶段失败，不把已部分变形的组作为有效值。
补偿重新安装全部原始键值、删除新增尾槽、还原原始归属与世代；创建失败则删除此次新建专属键。
补偿失败建立/保持ver2、原长度及奇数gen作为隔离控制元数据，读取器拒绝数值。
若连控制元数据也无法写入，返回严重后端错误-4，不声称保证隔离。
返回1成功，2补偿恢复，-1参数拒绝，-2状态/碰撞拒绝，-3隔离，-4后端控制失败。

原版分配/删除可改变桶地址、容量、节点排列和字符串地址，因此“精确恢复”指完整键/raw集合与归属一致。
不要求allocator布局逐字恢复；这与ZIP文件回滚的字节相等是不同验证。
所有假设仍限于同步稳定游戏线程，没有跨线程原子性保证。

## 真实游戏矩阵

本国、另一国、州、角色、global各10个独立fixture组，共50场景。
已有40组在执行形状变更前持久化包装基线并重开核对；创建和碰撞明确记录absence/preflight，不伪造合法基线。
初始已有组为raw [1234567890112500,-1]，同名scalar64=12345678901.125、原版数组[2.5,7.75]。

| 场景 | 实际结果 |
|---|---|
| create | 两个raw64最小值，gen2 |
| append | 添加raw64最大值，gen4 |
| insert | 中间插入raw64最小值，原邻居右移，gen4 |
| erase | 删除索引0，原索引1成为0，gen4 |
| resize up/down | grow填native2.5、shrink删除尾部，gen4 |
| clear | 专属数据/归属全部不存在，同名原版对象仍在 |
| rollback | 注入中途失败，完整容器键/raw集合恢复 |
| quarantine | 同时注入补偿失败，gen3并拒绝读取 |
| collision | 已有远端^4095孤立槽，create拒绝且集合不变 |

执行1100次原生put及160次真实erase，保留逐项记录。
最终206/206检查通过：35组成功、5组完整补偿、5组隔离、5组碰撞拒绝；相关解析错误0、游戏存活。
savegame ash内部ok=1且新存档确认；退出重启后50组仅只读核对，状态/数值和同名原版对象保持。
比较整个容器的排序键/raw映射，排除合法目标根后所有其他键不变；不扩大为整个进程内存无变化。

## 原生夹具与修正记录

同一C源码经MSVC /W4、有界模拟原生表和写删适配器执行287/287断言通过，stderr为空、退出码0，编译无警告。
覆盖create/clear/insert每个实际写删步骤的失败、create隔离、owner^后代碰撞、陈旧世代和非法索引，
64轮append/erase压力、零长度保留、4096创建及超限追加拒绝。
首次夹具错误地给clear不存在的22/23步骤注入失败，实际已成功完成而oracle期望补偿；已按真实21步骤修正。
首次游戏oracle把孤立键碰撞的Group_Read结果期待成“空闲0”，正确结果为“残余拒绝-3”；源码实际拒绝/无写入正确，已修正oracle。
失败unit_v1/result.json与native_v1/FAILED_oracle_comparison.json及原控制台仍保留，未报成首次全通过。
游戏中注入为逻辑拒绝步骤，不是访问异常、断电或引擎崩溃测试。

## 复现与接入顺序

报告目录test/reports/20261012_variable64_transaction/array_shape/native_v1。
复现：工程根 `python test/modules/effect/verify_array64_shape.py NEW_PHASE`，会建立独立fixture、记录、新存档并重启。
核对：`python test/modules/effect/verify_array64_shape.py native_v1 --verify-only`。
夹具：`python test/modules/effect/test_array64_shape_native.py OUTPUT_DIR`。
当前已证明成功/即时补偿或隔离，以及状态持久化；不是所有变长隔离状态均已能从文件自动恢复。
原进程内/文件导入恢复器要求固定完整形状，不能放宽它来盲补创建/删除后的缺槽与归属。
下一步把形状事务的操作意图/归属与基线接入恢复日志，验证重启后的创建中断、clear中断和缺槽恢复，再接公开脚本接口。
这属于原计划变长故障闭环，不另开研究方向；不因为讨论完成时间而降低验证要求。
多人、热读档、断电和全格式存档仍列明确未覆盖项；主线完成以接口可用与最终验收为准，不给未验证的日期承诺。
