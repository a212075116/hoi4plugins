# Trigger Tooltip 与单人生命周期验证

2026-10-12，当前本地 HOI4 1.19.3 Windows x64。对象：trigger_reg.c 的 Trigger_TypedTooltip / Trigger_ReadRawParameter。

## 已实现

数值与比较块改用定义自己的 locKey，不再复用“稳定度”文案或空的原版比较块 tooltip。
本地化参数固定为 LEFT、COMPARISON、RIGHT、RESULT，都是 text 参数；raw 保留 5 位小数精度并去尾零。
Trigger_FormatRaw 使用 unsigned magnitude，能够显示 LLONG_MIN，不做浮点转换或负极值取反。

显示六种比较符号，NOT 将符号转换成补关系并反转结果；有效结果使用本地化 TRUE/FALSE 的颜色。
未初始化参数、非法比较、直接随机 descriptor 则显示 UNAVAILABLE；随机 descriptor 的 tooltip 不调用参数读取器。
当前 helper 展示标准 raw 比较语义；若自定义 def.eval 为其他语义，应同步提供对应 tooltip，不要复用这个 helper。
实例里的原版 tooltip= 字段并非此 helper 的标签来源；本轮使用 def.locKey。

本轮 key 示例：

```text
PLUGIN_VALUE_HALF: "Half: $LEFT$ $COMPARISON$ $RIGHT$ ($RESULT$)"
PLUGIN_CHECK_VARIABLE64: "Variable64: $LEFT$ $COMPARISON$ $RIGHT$ ($RESULT$)"
PLUGIN_TRIGGER_RESULT_TRUE: "§GTRUE§!"
PLUGIN_TRIGGER_RESULT_FALSE: "§RFALSE§!"
PLUGIN_TRIGGER_RESULT_UNAVAILABLE: "§YUNAVAILABLE§!"
```

中英文 UTF-8 BOM 参考文件位于 test/modules/trigger/typed_tooltip_l_*_reference.yml。
DLL 不自动安装 mod 本地化文件，作者应复制对应语言文件到 mod/localisation。
本轮游戏 oracle 使用统一英文 fixture 字符串；中文参考文件已验证 UTF-8 BOM，但未单独做中文 UI 目视验收。
后续“同名变量最后设置者”阶段已安装真实中英文参考文件，中文原生文本 20/20 通过，
捕获“半值比较”“64 位变量比较”“满足/未满足”及颜色控制码。此后续结果仍不是 UI 悬停目视验收。

## 原生参数与上下文依据

CPdxLocalizeKeyValuePair 大小 0x68：type +0、key 指针 +8、备用 key 字符串 +16、文本 value +48。
ctor/dtor RVA 0x29DAD0 / 0x29DFE0；string ctor 0x11D970；pack 0x2245E60；format 0x10E48A0。
使用游戏的构造、分配、销毁；pack 后销毁四个参数，格式化后释放临时 packed/result 字符串。
回调不新增文件日志或跨回调缓存。原生输出中的颜色标记为 0x11；oracle 仅将此控制字节映射回 § 比较，原始文本保留。

必须传入原版 Tooltip 所需的真实 CEventScope，而不是日志 CContextLocalizationText。
两者即使都可读、scope helper 都返回 4，也不能据此认定可互换。
本轮正确 probe 在实际 custom evaluate 的 onEnter 生命周期内同步调用 tooltip，使用该回调的 self/context，
只存输出字符串，不在回调结束后复用 context 指针。
这是原生格式化和颜色控制码检查，不是鼠标悬停、界面布局或色彩的目视验收。

## temp 优先级缺陷与修复

基线：persistent variable64 dt_shadow=12345678901.125；同一事件的 temp dt_shadow=2.5。
原版 check_variable 等于 2.5 为真，自定义比较却为假，说明三槽读取错误覆盖了原版 temp 遮蔽规则。

新增 Trigger_HasTemporaryOperand，跟随原版 0x544C90 的分支：force-temp 标志与 scoped selector 规则；
临时系统 accessor 0x54F730，变量名 builder 0x5454A0，contains 0xBC8D20。
存在匹配 temp 时交回原版参数读取；不存在时才尝试 persistent 三槽读取。
不靠 temp 值与主槽值是否相等来猜优先级，不修改三槽、也不移除持久化变量。

本轮已验证：temp=2.5、同名 temp 遮蔽、缺失普通变量 equals 0、num_owned_states 动态参数，
自定义与原版所列条件一致。缺失的“完整变量引用”继承原版零值语义，不能与缺少 var/value 字段的空块混为一谈。
这是 Trigger 读取路径的修复，不代表 Effect 算术的全部同名 temp 场景已经验收。

## 结果与复现

| 验证 | 结果 |
|---|---|
| 游戏文本 | 10 组 × 正常/反转，20/20；覆盖大数、1e-5 负数、ROOT/global、temp/遮蔽、缺失变量、空块 |
| 原生 tooltip 夹具 | 16/16，含六种比较补关系、LLONG_MIN/MAX、无随机参数读取、临时参数 ctor/dtor 数量匹配 |
| 基线—修改—回滚夹具 | 1/16 →16/16 →1/16；基线/回滚 stdout 与退出码逐字相同，恢复源文件哈希相同 |
| 存档生命周期 | event.1 写入并保存 ttlife；保存返回 ok=1、有新文件；退出后 -continuelastsave 重启，再执行 event.2 |
| 重启读档 | marker=20261012、big=12345678901.125、negative=-0.00001、shadow=12345678901.125；读档后的 tooltip 正确 |

重启后的 shadow 恢复持久化大数，temp 值没有覆盖它。仅验证这些普通三槽值，不宣称挂账、所有 scope 或热加入已持久化。
原生夹具 mock 原版 allocator/formatter/container 依赖；ABI 和实际文字另由游戏 probe 验证。
本轮回滚为源文件夹具与完整 ZIP 的独立副本恢复，没有另行运行 DLL 游戏回滚。

入口：verify_trigger_tooltip_lifecycle.py PHASE --deploy --lifecycle（先完成构建，PHASE 全新）；
--attach 仅对已加载本轮事件与本地化的进程使用。原生入口 test_typed_tooltip_native.py SOURCE OUTPUT。

Evidence：test/reports/20261012_variable64_transaction/tooltip 的原生调用链记录、各轮 fixture/日志、samples、存档快照与 comparison。
Finding：参数 value 偏移、上下文类型和 temp 优先级是独立问题；仅看可读内存或 scope mask 不足以证明调用正确。
Path：保留失败阶段，纠正原生 binding 与 probe，再在真实 evaluate 回调里确认全部文本与存档重启结果，最后重跑回归。

## 保留的失败记录与边界

最初按字符串终止符读取日志变量名，误读 dt_result]；改用原版传入的 begin/end。
wrapper 并非每条优化路径都经过，已同时直接挂接注册日志中的真实 eval 地址。
最初 text value 写在 +16，游戏输出参数为空，mock 未发现；确认原生 binding 使用 +48 后同时修正源码和 mock。
最初在日志上下文调用变量 tooltip，局部参数读成 0；后来正确 API 的存档轮次因仍使用错误 probe 得到 14/20，已保留。
最终 verified_lifecycle 才是本轮生命周期验收记录。

尚未覆盖：全参数类型、动态变量同名冲突、数组/嵌套随机参数、所有前缀链与作用域存档、挂账、
热读档容器生命周期、多线程/长期 UI 运行、完整视觉验收和多人。多人顾虑继续见多人环境顾虑与协调测试.md。
