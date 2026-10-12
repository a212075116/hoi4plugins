# 数值、变量比较块与 Trigger Scope 适配

2026-10-12；当前本地 HOI4 1.19.3 Windows x64。单人优先；多人尚未验收。

## 新接口

| 接口 | 合约 |
|---|---|
| TRG_VALUE_DEF | 定点数值标量；callback 返回 raw（数值 ×100000），不是 float |
| TRG_VARIABLE_DEF | 原版 check_variable 参数块模板；默认 callback 比较两个解析后的 raw |
| TriggerScopeView | 仅包含原版 nativeContext 与原版 helper 返回的 scope mask；没有手工国家/州对象偏移 |
| Trigger_ScopeView | 初始化只在当前回调内有效的 view；NULL/不可读上下文返回失败 |
| Trigger_ReadRawParameter | 读取已初始化的 +88/+96/+296 descriptor；persistent variable64 用其自身容器，否则交回原版参数读取 |
| Trigger_CompareRaw | 六种整型 raw 比较；非法 token 返回 false，不做浮点转换或相减比较 |

`TriggerDef.parameterTemplate` 选择 BOOL/VALUE/VARIABLE；默认 0 保持旧 Bool 定义行为。
注册器按模板复制完整虚表/COL、原版 entry 析构和工厂；各模板分别验证 parse/eval/factory 地址。
数值模板有额外 getter，不能只复制旧 Bool 的 23 槽。定义和 callback 须维持进程生命周期。
这是三个确定的参数模板，不是任意字段的通用块 DSL；自定义语义可在 fill 后显式替换 def.eval。

## 用法与边界

```c
static long long __fastcall Half(void* self, const TriggerScopeView* scope)
{
    (void)self; (void)scope;
    return 50000;
}
TRG_VALUE_DEF(half, "my_half", "Half comparison", "MY_HALF", Half)
TRG_VARIABLE_DEF(compare, "my_compare_variable64", "Variable comparison", "MY_COMPARE")
```

fill 后通过 Trigger_RegistryRegisterAll 注册。示例实际名字为 plugin_value_half 与 plugin_check_variable64。

```text
plugin_value_half > 0.49999
plugin_value_half < ROOT.some_value
plugin_check_variable64 = { var = some_value value = ROOT.other_value compare = equals }
plugin_check_variable64 = { var = global.some_value value = 12345678901.125 compare = greater_than }
```

标量模板继承原版 CValueTrigger 的国家 scope 和严格 `>`/`<` 语法；不支持 `= yes` 或标量 `=`。
变量块继承 CCheckVariable 的不限特定 scope 与原版容器选择规则。
compare 接受 equals/not_equals/less_than/greater_than/less_than_or_equals/greater_than_or_equals；
省略 compare 时原版工厂默认 greater_than_or_equals，不应把它误当 equals。
Bool 的 yes/no 规则不套用到块条件；取反使用原版 NOT，组合使用原版 AND/OR。

未初始化的 descriptor（如空块或缺失 value）返回 false，不把工厂默认 0 与 0 的比较当成成功。
合法但不存在的普通变量、动态变量、temp、随机等仍有原版参数语义；未验证所有类型。
三槽变量读取失败不凭同名去其他容器找值；不会为读取创建 variable64 辅助槽。
目前只增强 persistent variable64 三槽读取，不重建进程内挂账，也不宣称挂账比较完整支持。

## 原生依据

| 模板 | 虚表 / 工厂 / parser / evaluator RVA |
|---|---|
| 数值标量 CHasStabilityTrigger | 0x27915A0 / 0x3E6A70 / 0x13A2690 / 0x13A2180 |
| 变量比较 CCheckVariable | 0x2799320 / 0x3E3E10 / 0x54AE70；块分派 0x438DC0 / 0x3D0BB0 |

数值实例 304 字节：比较 token +88，descriptor +96；复制 26 槽并覆盖 value getter +184。
变量实例 544 字节：descriptor +88/+296，比较 token +504；复制 23 槽。
两者仍由原版工厂构造，原版 parser 和析构保留。

原版 Trigger 包装 0x54D0B0、CCheckVariable evaluator 均调用 CEventScope 路径：
scope helper 0x537D90，参数读取 0x544C90，container resolver 0x542500。
本轮先从 Trigger 自身调用链确认这些共享路径，再接入 adapter；不是根据 Effect 名字猜布局。
view 不缓存指针跨读档/回调生命周期，也不是本地化 ctx。

## 三槽解码保护

新公开只读入口 Var64_ReadStoredContainerRaw 复用严格三槽身份验证。
针对用户手工构造的超范围 hi/lo/frac，新增有符号 raw 溢出拒绝；不执行溢出乘法。
同时接受等价的带借位表示（整数在边界外一位、小数向内补偿），避免误拒绝可表示负边界。
第一次保护版本在 2049 个输入中误拒绝 6 个等价边界表示，已保留红灯并修正，最终全部通过。

## Tooltip 与联机

后续已完成标准比较的自定义参数 Tooltip、temp 优先级修复与所列单人生命周期验证，
详见 [Tooltip与单人生命周期验证](Tooltip与单人生命周期验证.md)。下面是本模板首轮的历史限制，不作为最新完成状态。

Bool 保持已有自定义本地化文本；新模板暂复用原版参数感知 tooltip。
数值 getter 与求值 callback 一致；但标签仍可能是原版稳定度/变量比较文案，
原版变量 tooltip 尚未增强全部 variable64 数值展示。条件正确不代表 UI 展示完整，未做目视验收。

多人风险与协调步骤见 [多人环境顾虑与协调测试](多人环境顾虑与协调测试.md)。
当前回调只读、使用定点整数、无文件 I/O/墙钟/摄像机输入；这些约束降低风险，但不是多人通过证据。

## 验证入口

游戏：`python -u test/modules/trigger/verify_typed_triggers.py PHASE --deploy`（先完成构建，PHASE 全新）。
原生：`python test/modules/trigger/test_typed_trigger_native.py OUTPUT`。
解码：`python test/modules/effect/test_var64_stored_raw.py SOURCE OUTPUT`。
抗压：游戏加载含 zztypedtrg.2 的本轮事件后运行 run_typed_trigger_pressure.py PHASE。

Evidence：`test/reports/20261012_variable64_transaction/numeric/` 的 IDA 记录、事件、各端本地日志、comparison、原生输入/输出。
Finding：原版 parser/template 与自定义 raw 比较可组合；空参数、误用 Bool 槽数、三槽溢出均需独立防护。
Path：保留基线解析错误与假阳性，修改版断言全绿，独立 DLL 副本回滚后重现同输入基线，最终重新部署修改版。
四角色继续使用同一事务根目录，不覆盖此前阶段的验证记录。

## 本轮结果

| 验证 | 观察 |
|---|---|
| 同输入游戏基线 | 43/57，106 条未知 trigger 解析错误，注册标记不存在；正例假阳性不可当成功 |
| 修改版与最终重新部署 | 57/57，相关解析错误 0，四个容器中的大数文本不变，游戏存活 |
| 独立 DLL 副本回滚、同输入重启 | 与基线 57 行结果逐项一致，仍 43/57 和 106 条错误，原 DLL 哈希恢复 |
| 条件压力 | 1000 次真 AND 组合与 1000 次假 OR 组合；yes=1000/no=0，PREV/FROM、空块和缺失 RHS 检查通过 |
| 原生 typed API | 27/27，含 150 个极值比较输入、各自容器、严格标量边界、空参数与非法 token |
| 原生三槽 raw 解码 | 2049/2049；旧版与回滚版同输入各 26 个超范围失败，首次保护版误拒绝 6 个合法表示，最终修正 |
| 回归 | Bool 游戏 17/17、原生 Bool 22/22；Effect scope 12/12 +8 回调；variable64 516/516、旧断言 48/48/污染 0 |
| 其余原生夹具 | 饱和算术 10676/10676，身份 8/8，长名桥接 6/6；最终构建退出码 0，无警告 |

以上是该轮单人证据。后续格式化tooltip与所列dynamic/temp优先级已验证，见[Tooltip生命周期](Tooltip与单人生命周期验证.md)与[动态/数组隔离](动态同名与数组隔离验证.md)。全部缺失/动态/temp/随机语义、完整前缀链、
挂账比较、读档生命周期、多线程/长期推进和多人仍未全面验收。
