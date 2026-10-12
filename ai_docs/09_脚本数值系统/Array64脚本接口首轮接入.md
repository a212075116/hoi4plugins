# Array64 脚本接口首轮接入

2026-10-12，HOI4 1.19.3 Windows x64。array64_api.c已加入plugin.vcxproj并构建/部署真实DLL。
后端仅通过此入口整体编译，不要把其include链中的每个.c重复作为独立编译项加入工程。
这是首轮可用接口验证，不等于多人、所有存档格式和所有故障已完成最终验收。

## 真实语法

复用原版set_variable的var/value块参数，不是早期草案的array/index字段。
目标名1..20小写ASCII字母/数字/下划线，首字符字母；显式scope前缀由原版CScopedVariable解析。
全局用global.，ROOT/PREV/FROM与国家前缀按原版描述符解析；参数不自己拼scope指针。
索引用^，只求值一次，要求非负整数且<=4096；不会像原版名字构造一样静默截断小数索引。

```text
create_array64 = { var = example value = 2 }
set_array_element64 = { var = example^0 value = 12345678901.125 }
append_array64 = { var = example value = 5000000000.125 }
insert_array64 = { var = example^1 value = -0.00001 }
erase_array64 = { var = example^2 value = 0 }
resize_array64 = { var = example value = 4 }
set_array_element_native = { var = example^0 value = 2.5 }
log_array64 = { var = example^0 value = 0 }
if = {
    limit = { check_array64 = { var = example^0 value = 2.5 compare = equals } }
    log = "Array64 comparison succeeded"
}
if = {
    limit = { check_array64 = { var = example^num value = 4 compare = equals } }
    log = "Array64 count succeeded"
}
clear_array64 = { var = example value = 0 }
```

create的value为初始长度，全部填64模式0；resize的value为新长度，新增位置填64模式0。
append/insert/set的value为完整定点raw输入，支持已验证的原版scoped标量64操作数。
erase/clear/log的value=0作为原模板参数；未承诺额外max/自定义tooltip字段语义，应仅使用本文字段。
set_array_element_native只修改该元素并清零hi/kind，随后set_array_element64重新接管精度，不影响邻元素。
clear删除整个专属组；原版同名标量和原版数组独立，旧set_variable64=原版数组^index仍拒绝，不改成暗中操作Array64。
log不带^索引时记录长度，带^整数时记录该元素完整精度；查询^num用check_array64。
check支持equals、not_equals、greater_than、less_than等原版比较token；无效/缺失/隔离读取返回false，不猜0。

## 接入与scope身份

10个effect：create/append/insert/erase/clear/resize/set64/setnative/recover/log；1个block trigger check_array64。
effect工厂复用CSetVariableEffect原生实例，复制25槽虚表并保留COL，注册前指定正确变量参数entry parser。
trigger复用原生CCheckVariable块模板，只覆盖eval与只读左操作数；右值继续使用已验证的scoped raw reader。
Tooltip注册器新增可选operandReader回调，旧trigger默认NULL保持原逻辑。
已实测国家、另一国、州、角色、global。其他上下文仅按原版变量容器解析，不宣称覆盖全部scope对象。

首次成功创建前，每个实际原生变量容器生成四个安全31位随机标识并保存__v64sys_id0..3。
scope:32位十六进制标识是持久化容器身份，不是进程指针；重载重新解析容器并核对其标识。
生成使用BCryptGenRandom，不回退到时间/PID伪随机。部分或非法身份字段拒绝，不自作主张修复。
分支/组归属仍为专属组的随机标记；手工复制存档与侧车不自动视为新分支，须保留配对关系，不能宣称自动fork检测。
这些系统字段为保留数据，作者不能自行覆写。

## 日志、错误与恢复

操作前JournalPrepare→临时文件写入/FlushFileBuffers→MoveFileEx写透替换→重开逐字核对→Begin→Apply。
意图放在游戏根reports/array64_journal/<容器标识>/<逻辑名>.a64j，名称验证后构造路径，不接受外部路径参数。
成功与即时补偿清理原生事务标记；隔离保留意图。recover_array64={var=example value=0}显式读取本对象意图恢复或确认已完成清理。
不能因侧车不存在、nonce错配或外来归属而补造基线；没有任意文件导入入口。
当前按对象保留最近一项意图，不保证旧存档所有历史侧车均可追溯；文件配对/旧存档与崩溃生命周期还需最终矩阵验证。
正常文件刷新/替换不等于游戏存档与侧车联合原子提交。

每个effect写目标容器__v64sys_status：0成功；-901参数/索引错误；-902容器身份不可确认；-903分配、随机或文件错误；-904组读取不可用。
其余负码沿用后端碰撞、归属、nonce、状态拒绝；非0不能当成功。日志以[array64]和[array64-value]标识。
global目标状态也在global.__v64sys_status，不是调用者国家的状态槽。query只读，不更新status。

## 工具提示ABI与观察

原版变量effect的tooltip构造输出CString，不是追加到已构造字符串；首轮向未初始化输出append导致事件返回AV，已纠正。
effect tooltip现在先构造空输出，再追加安全文本；对literal value使用整数格式显示全部精度，scoped值显示runtime而不乱读UI上下文。
check工具提示使用原格式化/本地化流程，通过operandReader读取Array64，正常/反转数学值均可显示完整精度。
实际事件scope内调用过tooltip，effect测试故意把输出填0xA5验证构造ABI；正常/逆向12345678901.125比较字符串通过。
不声称已完成GUI悬停视觉验收；中文结果词的实际字节编码/视觉表现也未在本轮确认，数学数值与比较符已核对。

## 首轮验证与未完成

Release|x64构建退出0、stderr为空，部署后只使用公开脚本而非诊断CModule执行操作。
五scope创建/设置/插入/删除/resize/原版与64接管、ROOT标量64操作数、clear重建、缺失查询、碰撞/负长度/小数索引及新存档重启69/69通过。
同名scalar64=12345678901.125、原版数组[2.5,7.75]不变，相关fixture解析错误0。
已有原生trigger注册22/22、tooltip16/16、动态/数组边界8/8夹具再跑通过；不要把这些称为全部历史回归。
旧同名setter真实五scope与存档往返再跑57/57通过；本接口tooltip原生调用4/4通过，尚非GUI视觉通过。
首轮事件虽已执行大多数效果但内部ok=0/AV，不保存、不算通过，失败日志与tooltip反编译保留。
本轮编入并注册的是实际接口，不再把它描述为仅诊断后端；最终发布仍待恢复/异常/压力完整矩阵与视觉检查。
主证据test/reports/20261012_variable64_transaction/api/native_final，驱动verify_array64_api.py。
多人需协调系统身份/侧车归属、操作排序/随机ID、存档校验和、各端文件读写；本轮仅单人，不承诺多人可用。
