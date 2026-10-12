# Array64 持久化快照与重载绑定

2026-10-12，HOI4 1.19.3 Windows x64。仅独立诊断CModule，已有固定长度组，公开API继续关闭。
源码array64_durable_snapshot.c在进程内Capture/Recover之上增加ExportBaseline与ImportBaseline。

## 文件格式与边界

记录不是Array64Snapshot结构体内存转储，不保存指针、owner token、padding或ABI布局。
所有整数明确为little-endian；负raw使用64位二进制补码，导入不依赖实现定义的unsigned转signed溢出。

| 字节偏移 | 字段 |
|---|---|
| 0..7 | ASCII A64BASE2 |
| 8..11 | 记录版本1 |
| 12..15 | 数值协议版本2 |
| 16..19 | 元素数0..4096 |
| 20..23 | 基线偶数世代0..2147483644 |
| 24..31 | 调用方确认的非零存档/campaign lineage |
| 32..35 | scope身份字节数1..80 |
| 36..39 | 逻辑名字节数1..20 |
| 40起 | scope ASCII、逻辑名ASCII、每元素lo/hi/kind的三个signed64 raw |
| 最后8字节 | 前面全部字节的FNV64校验和 |

总字节数严格为48+scope长度+名字长度+24×元素数，不接受额外尾部、截断或整数长度溢出。
scope规范为country:三位大写tag、state:非零规范十进制ID、character:稳定脚本键或global。
禁止state前导零/超限、嵌入NUL和非规范字符串；逻辑名沿用1..20小写ASCII规则。
记录版本与数值协议版本分别验证；未知版本拒绝，不自动迁移。
FNV用于意外损坏检测，不是密码学认证。测试宿主另保存SHA256并重开文件核对，也不代表签名或防恶意篡改认证。

## 导出与重新绑定

导出只接受未消费、完整且校验通过的进程内快照；输出容量不足时不写输出和written哨兵。
导入先验证版本、长度、校验、scope/name/lineage，再检查当前原生隔离组的完整形状。
当前odd必须等于记录基线gen+1，长度必须一致，每个槽仍存在；不在此入口创建或补造缺失键。
校验通过后用新解析的container和当前会话owner重建进程内快照、重新计算其内存校验和。
恢复仍由Array64_Recover执行，提交新的偶数世代。旧文件不能在新偶数状态或更晚隔离世代重复导入。

| 导入返回 | 意义 |
|---|---|
| 1 | 可供显式恢复的当前会话快照已建立，尚未修改游戏 |
| -1 | 参数、当前容器、owner或调用方scope无效 |
| -2 | magic、文件版本或协议不支持 |
| -3 | 长度、校验、名称或编码损坏 |
| -4 | scope、逻辑名或lineage不匹配 |
| -5 | 当前隔离形状/长度/世代不匹配，包含陈旧和重放 |

导入拒绝时使输出快照失效，且不调用原生写适配器；不能继续使用上次导入成功的旧buffer。
容器与语义身份关系必须由可信宿主独立确认，不能从文件scope选择任意对象再直接信任。

## 真实重启验证

驱动verify_array64_durable.py在五scope各准备txpersist/txstale两组，保留同名scalar64与原版数组。
txstale另保留gen2旧记录，并在成功更新到raw64最小值/gen4后导出当前记录，以验证旧基线拒绝。
使用独立的zzads.1准备事件和zzads.2隔离事件，中间先将记录写临时文件、flush/fsync、replace，重开核对全部内容。
隔离前确认10个当前记录已落盘；共15个.a64文件（另5个旧基线），然后才执行故障隔离。
savegame ads内部ok=1且新存档确认；退出重启后仅从实际文件读取，不复用旧进程快照或容器指针。
zzads.3解析新容器，读取容器中持久化ds_scopeid/ds_lineage标记，使用控制器预先确认的scope映射绑定。
10个组恢复成功：普通组gen3→4恢复原值，陈旧测试组gen5→6恢复raw最小值；邻元素raw=-1不变。
重载后70次原生槽写入有前后值记录；同名scalar64=12345678901.125和原版数组[2.5,7.75]不变。
跨scope及其他scope实际文件、错误lineage、坏校验、未知版本、截断、陈旧基线和恢复后文件重放均拒绝且无写入。
独立Python解析15个真实文件，按明确字节格式与FNV重新计算并解码，核对scope、世代和数值，不使用C解码函数作自身oracle。
最终167/167检查通过，包含15项独立文件oracle；write20个、reload10个样本，相关解析错误0且游戏存活。

身份范围要明确：ds_scopeid是可信fixture在相应原版scope中写入的标记，不是通用引擎对象身份查询API。
本轮lineage使用固定测试标记，仅验证字段匹配/拒绝；生产须分配唯一、稳定且可独立核对的campaign/分支身份。
同一lineage下若删除重建组、回绕世代或复制分支导致名称/世代再度相同，尚需组incarnation机制；不能声称这类重放已解决。
记录落盘顺序经过正常运行测试，不代表断电、文件系统崩溃或游戏存档与侧车文件已构成原子事务。
准备阶段的成功更新不等于所有未来公开写入都已接入先落盘日志；当前不开放API。

## 原生夹具与证据

同一C代码经MSVC /W4有界模拟原生布局执行411/411断言通过，stderr为空、退出码0，最终编译无警告。
包括格式头、独立owner绑定、scope/lineage/name拒绝、截断/超限长度、内嵌NUL、重算校验但非法编码、
容量不足不写、陈旧/重放、64轮极值导出导入恢复和4096元素/20字节逻辑名记录。
这是模拟内存夹具，不能替代上述五scope真实重启证据。
首次宿主记录遍历时修改字典导致RuntimeError，退出1，未进入隔离/保存；已改为遍历独立条目列表并使用新阶段重新启动验证。
失败控制台和部分记录保留在array_durable/native_v1，不算通过。

证据：test/reports/20261012_variable64_transaction/array_durable/native_v2。
复现：工程根执行 `python test/modules/effect/verify_array64_durable.py NEW_PHASE`，会重启游戏、创建fixture记录、保存ads并再次重启恢复。
核对：`python test/modules/effect/verify_array64_durable.py native_v2 --verify-only`。
夹具：`python test/modules/effect/test_array64_durable_native.py OUTPUT_DIR`。

## 下一步

先补生产级稳定scope/campaign与组incarnation绑定、侧车缺失/错配和存档分支生命周期矩阵，再推进创建和变长。
公开接口、缺槽恢复、数组插入删除、热读档、长期压力、全格式存档和多人一致性仍未完成。
多人还需协调侧车记录分发/归属、各端存档lineage与世代、事件排序及同步线程；本轮仅单人，不承诺多人安全。
