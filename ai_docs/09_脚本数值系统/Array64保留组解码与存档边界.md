# Array64 保留组只读解码与存档边界

2026-10-12。独立诊断后端 Array64Group_Read，未编入生产插件，未开放写入API。
承接已实测的NativeArray_Read；本轮读取真实原生隐藏键组，而非仅恢复模型JSON。

## 发现：协议v1不能安全保存signed32最小分量

v1使用signed low32/high32 ×100000，运行时可正确读出整个raw64域。
真实savegame aggroup成功且产生新文件，退出重启后却发现raw64最小值变成0。
存档原文：`__v64a_shared_hi^1=--2147483648`，五scope均出现；原始运行时hi分量是-2147483648。
这是原版文本格式化边界的实际损坏，不是后端解码精度或浮点转换问题。
正向越界分量2147483648还会被写成-2147483648。损坏夹具不能假定存档序列化恒等。
失败证据：array_group/native_v1/FAILED_v1_comparison.json、write/reload_samples.json、save_snapshot.hoi4。
原始v1后端单独保存在array_group/FAILED_v1_backend.c，不将失败轮次报告为通过。

## 修正：候选协议v2与转义分量

清单ver=2；v1和未知版本一律拒绝，没有自动迁移或猜测旧值。
其余清单与三列键沿用__v64a_NAME_{ver,gen,len,lo,hi,kind}。
64位模式把raw拆为signed32低/高分量，特殊值-2147483648使用0占位并在kind声明转义。

| kind逻辑值（存储raw再×100000） | 解码 |
|---|---|
| 0 | 原版精度raw保存在lo，hi必须0 |
| 1 | 普通signed32低/高分量 |
| 2 | lo占位必须0，解码时恢复低分量-2147483648 |
| 3 | hi占位必须0，解码时恢复高分量-2147483648 |
| 4 | lo/hi占位均必须0，解码时恢复两项最小分量 |

非转义分量范围[-2147483647,2147483647]，必须为整数×100000；不得出现裸的-2147483648。
重建raw=high×4294967296+unsigned(low)，采用有界signed64算术，不左移负数、不经过double。
kind0要求hi=0且-214748364800000 < lo_raw < 214748364800000。
这是首版保守的原生模式保存范围，不代表原版所有变量可表示范围。
因此全raw64域由kind1..4支持，native setter必须先遵守原版转换规则及此保存范围，不接受任意raw64冒充原版模式。

## 读取与碰撞检查

接口：Array64Group_Read(container,name,index,expected_generation,output,count,generation)。
name限定1..20小写ASCII，首字母；container由原版有效scope现场解析。
expected_generation=-1表示无缓存版本要求，其他值必须与清单一致；不保存进程内指针。
先扫描容器中实际占用节点，识别六个精确保留根键及其^后代。
按完整根键边界判断，不用逻辑名粗前缀；demo和demo_lo可以独立存在。
缺清单但存在残余元素（包括远端^4095）视为碰撞，不能因^num不存在而覆盖。
合法组必须恰有6+3×len个所属键；多出的元素、列基础标量、清单下的数组键均拒绝。
此扫描针对六个协议根，不声称探测任意未知后缀；不可读/损坏表不能判为空闲。
每次读取校验三列长度并逐个解码所有元素，即使错误在未请求的索引也拒绝整组。
缺失元素、额外键和列长度不一致不能静默填0、截断或修复。

| 返回 | 含义 |
|---|---|
| 1 | 完整组合法且索引有效，输出raw/count/generation |
| 2 | 完整组合法但索引越界，含显式空组，输出count/generation，raw保持 |
| 0 | 清单及六根所属键均不存在 |
| -1 | 参数、名称、内存或表不可确认 |
| -2 | 清单不完整 |
| -3 | 残余/额外所属键或键数量不匹配 |
| -4 | 不支持的版本 |
| -5 | 奇数、负、小数或超限世代 |
| -6 | 负、小数或超限长度 |
| -7 | 列长度/元素形状错误 |
| -8 | kind、分量或native模式编码非法 |
| -9 | 缓存世代不匹配 |

所有拒绝和不存在状态保持输出哨兵，不将失败转换成0。
本轮只能在同步游戏线程稳定现场读取；多次检查不是原子事务，未提供并发写保护。
全容器扫描加整组校验有明显成本，目前仅用于诊断与接入验证，不注册为高频trigger。

## 执行证据与范围

同一份C源码分别经MSVC有界原生布局夹具及Frida CModule执行。
游戏测试由原版set_variable/add_to_array构造测试专属保留组；这些fixture写入不是新的Array64写入API。
保存新aggroup存档、退出、-continuelastsave重启后，重新解析本国/另一国/州/角色/global容器。
覆盖20字节逻辑名、完整raw64极值、负1最低小数单位、native2.5、空组、缺失、孤立远端元素、
部分清单、v1拒绝、奇数世代、小数长度、不同列长、坏kind、小数/越界分量、native-hi残留与额外键。
读前后比对容器头与桶表含spill；仅对这些观察区域声明无变化。
纯C夹具另覆盖低/高/双转义、转义占位不为0、随机signed64、非请求元素损坏及4096长度形状。
实际数量、stdout/stderr、命令内部ok、新文件哈希及状态保存在array_group下的报告和事务VERIFICATION.txt。
最终v2游戏往返52/52检查通过，write/reload各45个同步callback样本全部核对，相关解析错误0、进程存活。
MSVC /W4有界原生夹具2084/2084断言通过，stderr为空、退出码0，编译无警告。
随机检验覆盖2048个signed64样本；不是枚举整个64位空间，不代表所有存档格式均已验证。

复现：工程根执行 `python test/modules/effect/verify_array64_group.py NEW_PHASE`，会重启游戏并生成专属事件与aggroup存档。
离线核对：`python test/modules/effect/verify_array64_group.py native_v2 --verify-only`。
原生夹具：`python test/modules/effect/test_array64_group_native.py OUTPUT_DIR`。

仍未证明写入/补偿原子性、清理/扩容ABI、运行中热读档、全格式存档或多人一致性。
多人需协调各端事件执行顺序、索引/随机求值、世代/存档校验和及是否可在同步线程执行。
下一步先验证可逆写入后端与故障隔离流程，不因只读解码通过提前开放公开写入。
