import pathlib,re,sys
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
def write(name,text):(ROOT/name).write_text(text.strip()+'\n',encoding='utf-8')
def edit(name,old,new):
    p=ROOT/name;s=p.read_text(encoding='utf-8-sig');assert old in s,(name,old);p.write_text(s.replace(old,new),encoding='utf-8')
def history(name,latest):
    p=ROOT/name;s=p.read_text(encoding='utf-8-sig');at=s.find('\n')
    s=s[:at+1]+f'\n> 历史阶段记录：全文的“本轮/当前/下一步”仅指当时实验，不是最新状态或可直接照抄的实施指令。现状见 [{latest}]({latest}.md)。旧方案、失败与旧偏移保留用于追溯，不覆盖现实现。\n'+s[at+1:]
    write(name,s)

# Preserve complete bodies at section boundaries, rather than truncating them.
folder='ai_docs/09_脚本数值系统/'
for original,marker,parts in [
 ('variable64实现与验证.md','## 二十一、',[('variable64历史_语法探索.md','语法探索'),('variable64历史_模板复用与早期边界.md','模板复用与早期边界')]),
 ('作用域与effect实例.md','## 十七、',[('作用域历史_诊断与实例化.md','诊断与实例化'),('作用域历史_读写与语法探索.md','读写与语法探索')]),
 ('变量存储结构.md','## 十四、',[('变量存储历史_早期查表与CE实验.md','早期查表与CE实验'),('变量存储历史_描述符与容器定位.md','描述符与容器定位')]),
]:
    s=(ROOT/folder/original).read_text(encoding='utf-8-sig');index=s.index(marker)
    for (name,label),body in zip(parts,[s[:index],s[index:]]):
        assert not (ROOT/folder/name).exists(),name
        write(folder+name,f'# {label}（历史证据）\n\n> 本文只保存当轮探索、失败和旧方案，不是当前操作手册。已推翻的布局/名字长度/回绕/两槽假设不得沿用；当前实现见[当前状态与复现](当前状态与复现.md)。\n\n'+body)
    if original!='变量存储结构.md':
        write(folder+original,f'# {original[:-3]}：当前入口与历史索引\n\n当前功能、名字边界、三分量与存读档结论见[当前状态与复现](当前状态与复现.md)。\n原始探索全文按章节拆分，没有删掉失败证据：\n\n'+''.join(f'- [{label}]({name})\n' for name,label in parts)+'\n旧固定名字、12字符上限、两槽、自然回绕及“存档待测”等结论只适用于历史候选。当前主名33字节、辅助槽40字节，使用_var64h/_var64f；读档、scoped参数、typed trigger与Array64均已有所列验证。\n')

write(folder+'变量存储结构.md','''# 游戏变量存储：当前确认布局

核对：HOI4 1.19.3 x64；依据现有native_array_readonly.c、array64_group_readonly.c、variable64.c及空表/游戏存档验证。
不是把早期CScopedVariable描述符当作真正变量容器，也不能从一个节点地址倒推出容器。

## 定位与哈希表

Effect目标描述符由原版resolver RVA 0x542500解析为实际变量容器；upsert RVA 0xBC5C10，erase RVA 0xBC8FC0。
只读身份/查询不调用upsert，避免因查询制造变量。跨新增/删除不得缓存节点地址。

| 相对实际容器 | 当前用途 |
|---|---|
| +24 | 独立分配的桶数组指针 |
| +32 | 空表检查使用的计数字段 |
| +36 | mask，普通表为2^k-1 |
| +40 | spill阈值字节 |

48字节节点：hash在+0、探测距离字节+4、名字std::string在+8、长度+24、容量+32、signed raw值+40（8字节）。
FNV-1a 32位哈希；Robin Hood连续探测，不能错误地把每次探测绕回mask范围。
SSO容量15；长名按指针/实际容量读取，不把长名字塞进15字节内联区。
旧文的“表+20”相当于“容器+36”，两个参照基址不能混用；旧内联桶/描述符+160容器猜测已被后续定位替代。

## 合法空表

mask=0的未分配容器可以使用静态空哨兵；仅计数0、spill0、哨兵可读且未占用时判为合法不存在。
NULL表、异常计数/spill或已占用哨兵仍拒绝。这个修复覆盖角色首次create Array64，见[恢复与压力验收](Array64恢复与压力首轮验收.md)。

## 原版、scalar64与Array64

原生槽是8字节raw定点值，scale=100000；这不表示原版所有运算自动获得完整64位精度。
原版数组不是vector：物理键为name^num和name^index；增加、删除、移位和哈希表重排会改变节点位置。
scalar64使用主名及_var64h/_var64f三槽；Array64使用独立__v64a_NAME三列/清单、__v64o归属和__v64t事务标记。
各方案必须分别验证身份、编码、generation及持久化，不能相互套用。

## 历史与限制

- [早期查表与CE实验](变量存储历史_早期查表与CE实验.md)：保留初期假设与当轮数据。
- [描述符与容器定位](变量存储历史_描述符与容器定位.md)：保留纠正过程。
- 当前名字、精度及存档状态：[当前状态与复现](当前状态与复现.md)。

本轮是文档核对，不重新验证全部RVA；其他游戏版本必须重新查证，不能默认沿用。
''')

write(folder+'变量与定点数.md','''# 脚本变量的raw存储、精度与上限

依据HOI4 1.19.3现有原生槽解码、CSetVariable执行路径及variable64实测，不把早期类型推断当当前结论。

## 必须区分的三件事

1. 物理槽：48字节节点+40是8字节signed raw，scale=100000，已实测小数。
2. 原版语义：参数转换、整数部分范围和运算路径可能限制/截断精度；物理槽宽不等于原版所有运算都支持raw64全域。
3. 插件语义：scalar64通过三分量和专用hook保留真值；Array64通过独立版本化三列存储，不改变原版同名数组。

早期原版set_variable边界记录包含2147483647成功、2147483648翻负及乘除异常小数；这些是对应原版路径的历史观察，不证明存储槽只有4字节。
原版最小signed32分量曾在文本存档形成双负号；Array64 v2用kind转义该分量，不按显示文本推测底层布局。

## 当前插件方案

scalar64辅助后缀为_var64h/_var64f，主名最多33字节、辅助槽40字节；不是早期_hi双槽或12字符上限。
raw64表示值×100000，受signed int64范围限制；自定义效果、原版算术hook、挂账、动态/temp优先级必须按各自已验证合约使用。
不能笼统写“只改计算无效”或“唯一方案是手工双变量”：现实现已采用可存档三分量、身份识别和原版log桥接。
同容器同名变量的最后setter规则见[最后设置者](同名变量最后设置者规则.md)。

## 版本与来源边界

旧文将上限变化外推为“2026-05官方去掉小数”的完整版本历史，没有列出可核对的补丁来源；本页撤回该外推。
这不撤销原有具体输入/输出记录。旧实验报告保留在test/reports/，新结论依据当前源码和所列存档/算术验证。
没有必要或证据去整体替换引擎全部数值类型；当前可用的局部方案不等于对所有原版变量、存档和动态链无条件兼容。

参见[存储结构](变量存储结构.md)、[当前状态](当前状态与复现.md)、[Array64单人交付](Array64单人交付说明.md)。
''')

write(folder+'当前状态与复现.md','''# 脚本数值系统当前状态

核对日期2026-10-12；当前生产DLL SHA256为72704dfaa4cc5485425841a19a34f38a866bc88c9f72a7743b1dcc7ca9b41070。
生产variable64.c SHA256为ec54864342e9e8811aaea73eb7ef66ed5f4f9328a7083854120f190880755c1e。
这是当前结论入口；历史文章里的“本轮/下一步”不覆盖本页。本次文档整理不重跑游戏、不宣称所有旧测试重新验收。

## 功能主线

| 模块 | 当前已确认 | 边界/入口 |
|---|---|---|
| scalar64 | 原版var/value语法、三分量、真实小数log、普通存档重启、最后setter规则 | 主名33字节、辅助40字节；_var64h/_var64f |
| 原版算术兼容 | 加减乘除、变量操作数及clamp min/max所列验证；32/64挂账参与真值计算 | 原版round/modulo同名hook仍停用，独立_64入口另计 |
| scope | 国家/州/角色/global原版容器规则；ROOT/PREV/FROM/global所列持久化操作数 | 不把Any mask等同global，也不保证全部前缀链 |
| Trigger | Bool、VALUE、VARIABLE模板与typed adapter、比较、tooltip原生格式化 | 动态/temp优先级及原版数组索引隔离已有专项证据 |
| Array64 | 已正式编入DLL，10个effect+check_array64；创建/变长/精度切换/清理/恢复 | v2三列；不接管原版同名数组，scalar64原版数组索引仍拒绝 |
| UI 颜色 | 用户明确确认已解决 | 不与新tooltip GUI视觉尚未验收混为一谈 |

参见[最后setter](同名变量最后设置者规则.md)、[读档与抗压](读档身份与抗压验证.md)、[Scope](../08_Effect系统/Scope与scoped操作数验证.md)、[typed Trigger](../10_Trigger系统/数值块模板与Scope适配.md)。

## 分轮证据，不能相加为本次全量重测

| 阶段 | 已记录结果 |
|---|---|
| scalar64首轮复现/长名修复 | 选定48/48；桥接6/6；新存档WRITE/READ完整小数一致 |
| scalar64扩展压力 | 516/516；身份8/8；整数oracle10676/10676 |
| typed Trigger | 游戏57/57，typed夹具27/27及所列条件压力 |
| setter所有权 | 五scope及存档57/57；原生与64切换不永久粘连 |
| Array64正式接口 | 69/69，五scope/ROOT/同名隔离/存读档 |
| Array64公开恢复与压力 | 330/330，25例异常侧车、810次操作和4096边界 |
| Array64归属/旧存档 | 338/338；错receipt、branch、incarnation、身份及侧车配对 |
| 真实中断与持续操作 | 137/137；三个确定性实际终止门；181.98秒6600次操作和重载 |
| 空表/日志/tooltip后端 | 空表2091/2091、日志244/244、Array64原生tooltip4/4 |

各后端C文件通过array64_api.c的include链进入同一编译单元，不应逐个加入vcxproj重复编译。
诊断CModule旧报告仍是历史证据，不能据其旧“公开API关闭”描述认为当前未接入。
最新使用、备份与限制统一见[单人交付](Array64单人交付说明.md)。

## 最新资源观测与真正剩余项

压力期私有内存约+283MiB；随后180秒空闲约-3MiB。资源增长尚未归因，不能宣称资源发布验收通过。
下一步应先做等调用数空事件、原版平衡数组和Array64对照，而不是重复已完成的中断门或盲目延长到多小时。
GUI悬停/中文结果词视觉、多人、掉电/硬件持久性、任意崩溃点、多小时soak、运行中热读档与完整作用域/动态参数矩阵仍未全面验收。
Array64只保留最近意图，旧存档需精确配对备份；原生容器身份不自动识别复制存档fork。孤儿.tmp尚无自动清理。
当前测试状态已推进到a64soak与五份配对侧车；旧recovery_v3/lifecycle_v1身份记录不能无条件当作最新运行前提。
详见[真实中断与资源](Array64真实中断与定时持续运行验收.md)。

## 复现与证据入口

- [数值系统测试入口](../../test/docs/numeric_system.md)：区分可重建fixture与要求特定旧检查点的驱动。
- 历史语言桥接复现：test/modules/effect/reproduce_variable64.py及verify_variable64_reproduction.py，证据test/reports/20261012_variable64_reproduction/modified/。
- 最新Array64证据：test/reports/20261012_variable64_transaction/api/crash_soak_v4/。
- 旧验证中的long-name/GBK/工具提示ABI/宿主指针与死亡判断失败原文仍保留；失败不算成功，无新存档不冒充旧存档重载。
- 所有RVA与ABI限定所列版本；本次仅核对文档和现有证据，不扩大为其他游戏版本已验证。
''')

# Earlier phase reports remain useful, but their deployment claims are historical.
historical=['Array64保留组解码与存档边界.md','Array64创建变长与原生删除事务.md','Array64变长意图日志与重启修复.md','Array64固定长度事务与失败隔离.md','Array64归属生命周期与收尾范围.md','Array64持久化快照与重载绑定.md','Array64显式恢复与运行时压力.md','原生数组只读后端与验证.md','variable64的effect实现.md','变量溢出挂账机制.md','变量运算effect的64位版.md','变量运算符64位接入.md','log64位桥接.md','log输出链路.md','set_variable执行路径.md']
for name in historical:history(folder+name,'当前状态与复现')
history('ai_docs/08_Effect系统/注册新Effect_实测记录.md','注册器API')
history('ai_docs/08_Effect系统/Effect系统结构.md','注册器API')
for name in ['CResistance启用机制.md','CResistance修复实验.md','CState与CResistance.md']:
    p=ROOT/'ai_docs/06_游戏结构'/name;s=p.read_text(encoding='utf-8');at=s.find('\n');write(p.relative_to(ROOT).as_posix(),s[:at+1]+'\n> 该页是对应抵抗实验的结构/状态记录，不是当前模组配置快照；本次未重测抵抗模块或外部mod文件。实验中的待查项保持待查，不能据别的模块通过而标为解决。\n'+s[at+1:])

edit(folder+'Array64显式协议设计.md','# Array64 显式协议设计 v2（只读验证，写入未开放）','# Array64 显式协议设计 v2（当前存储协议与历史模型）')
edit(folder+'Array64显式协议设计.md','本页为当前候选协议；v1模型通过不等于v1真实存档通过。真实边界损坏已促使版本升级为v2，仍不是完整array64发布说明。','v2已用于正式Array64接口；v1交互模型仍是历史原型，不等于v2存档验收。使用方式与最新限制见[单人交付说明](Array64单人交付说明.md)。')
p=ROOT/folder/'Array64显式协议设计.md';s=p.read_text(encoding='utf-8');start=s.index('原生数组只读后端、v2隐藏键文本保存');write(p.relative_to(ROOT).as_posix(),s[:start]+'## 后续实现状态\n\n正式创建/变长/恢复与脚本接口已经接入，不能沿用原设计阶段的“只读/写入未实现”状态。\n真实中断与6600次有界压力已有记录，资源增长、多人/多线程、完整视觉与掉电仍未全面验收。详见[当前状态](当前状态与复现.md)。\n')

# Correct current tables rather than only hiding them behind a history label.
p=ROOT/folder/'变量系统类与函数.md';s=p.read_text(encoding='utf-8');a=s.index('## 五、还没找到的');b=s.index('## 七、相关文档');s=s[:a]+'''## 五、现已定位的接口

| 目标 | 当前结论 |
|---|---|
| CSetVariable exec | RVA 0x364C60；原生工厂0x341F60；变量参数entry模板0x277C418 |
| 实际变量容器 | resolver RVA 0x542500；不能把CScopedVariable描述符+160直接当容器 |
| raw查表/写入 | 当前只读查找与原版upsert/erase已用于scalar64/Array64；布局见[存储结构](变量存储结构.md) |
| 块var/value解析 | 原版模板复用已实现；不需要在54x参数函数里另造块字段解析器 |
| 保存重启 | scalar64三分量与Array64隐藏组所列文本存档往返已验证；热读档/全部格式仍非全面证明 |
| Trigger注册 | Bool、VALUE、VARIABLE已实现，见[typed模板](../10_Trigger系统/数值块模板与Scope适配.md) |

上方地址清单保留对应静态查证范围；不因这些接口定位完成而声称全部变量类、所有动态参数语义已验证。

'''+s[b:];write(p.relative_to(ROOT).as_posix(),s)
edit(folder+'log与变量格式化.md','**上限就是 int32 的 `2147483647`**，与 `set_variable` 的存储位宽一致。','这些是对应原版转换/显示路径的边界，不代表物理槽仅4字节。原生槽为8字节raw，见[存储结构](变量存储结构.md)。')
edit(folder+'log与变量格式化.md','描述里只举了 K 和 M，**没有 G（十亿）或 T（万亿）**。','该本地wiki摘录只举K/M；未举例不等于证明引擎不支持其他后缀。本文不将这一缺省例证视为完整范围结论。')

# File moves and source-level initialization facts.
for name in ['ai_docs/05_工具链/idalib常驻服务.md']:
    p=ROOT/name;s=p.read_text(encoding='utf-8');s=s.replace('test/tools/idalib_','test/lib/idalib_').replace('test/probes_frida/frida_host.py','test/lib/frida_host.py');s=s.replace('新脚本请参照 `test/probes_js/` + `test/tools/*_run.py` 的现行写法。','新脚本参照test/lib公共库与test/modules现有驱动；历史probes目录不是现行入口。');write(name,s)
edit('ai_docs/01_工程与构建/构建方式.md','`test/_strip_comments.py`','`test/tools/strip_comments.py`')
edit('ai_docs/01_工程与构建/构建方式.md','产物落在 `build/Release/`：`tbb.dll` 与 `hoi4_mod_plugin.dll`。','产物落在 `build/Release/`：`tbb.dll` 与 `hoi4_mod_plugin.dll`。\n\n单独构建src/plugin/plugin.vcxproj时必须传入工程根的SolutionDir，否则产物可能落入src/plugin/build/Release，部署器仍读取根build/Release，造成旧DLL误部署。优先构建整个解决方案；部署后核对构建、游戏根和归档DLL的SHA-256。')
write('ai_docs/03_插件/插件入口.md','''# 插件入口与初始化顺序

依据src/plugin/plugin_main.c；产物hoi4_mod_plugin.dll，由载体按绝对路径LoadLibrary加载，不转发游戏导出。

## 当前源码顺序

DllMain仅DisableThreadLibraryCalls、建立PluginThread并关闭线程句柄；不是在DllMain执行注册/扫描重活。
此前标题“为什么不在DllMain建线程”与实际代码冲突：载体CRT时序与插件创建初始化线程是不同问题。

PluginThread先初始化日志/文件重定向等模块，接着：
1. 轮询Effect lexer就绪，注册摄像机、日期、scalar64、Array64 effect及loadgame命令/语言桥接。
2. 独立轮询Trigger注册器，注册三个demo与check_array64；检查各模块日志中的实际成功数。
3. 等CGameState全局槽可读/非NULL，验证类结构；这不等同进地图。
4. 捕获摄像机上限，注册摄像机、日期及崩溃测试控制台命令，之后扫描已知类数组。

Camera_RegisterCommands标记仅证明初始化到了这一阶段，不独立保证所有effect/trigger成功或地图可用。
地图/旧存档就绪需结合game.log标记、idler及测试驱动稳定期；见[启动与就绪](../05_工具链/启动与就绪判断.md)。
日志为游戏根reports/mod_loader_tbb.log。本页不把某次PID、绝对地址或耗时当跨运行常量。
''')
edit('ai_docs/08_Effect系统/注册器API.md','使用者只需在 `fill` 里填 `name`/`desc`/`locKey`/`exec`（宏已代劳）。','默认EFF_DEF填name/desc/locKey/exec/factory/tooltip。\n可选EffectDef.entryParser在注册前指定原生entry参数模板；NULL保留stability模板。Array64预先设置变量parser并用自己的原生工厂/虚表；不要把所有自定义effect都当作stability布局。scalar64现有路径仍在注册后patch entryVt[0]，不能误称两者完全一样。')

# Current source tree and include list; old drawing omitted added modules.
edit('ai_docs/01_工程与构建/目录结构.md','│           └─ hook/            IAT 钩子','│           ├─ trigger/         Bool/typed Trigger注册、比较与tooltip\n│           ├─ variable64/      scalar64与Array64（API单编译单元include后端）\n│           ├─ gamedate/        日期与界面刷新\n│           ├─ crash_test/      独立崩溃测试命令\n│           ├─ minihook/        第三方MinHook\n│           └─ hook/            IAT/inline封装、文件与进程钩子')
edit('ai_docs/01_工程与构建/目录结构.md','$(ProjectDir)SDK_RVA\\effect;$(ProjectDir)SDK_RVA\\hook;..\\carrier','$(ProjectDir)SDK_RVA\\effect;$(ProjectDir)SDK_RVA\\trigger;$(ProjectDir)SDK_RVA\\gamedate;$(ProjectDir)SDK_RVA\\crash_test;$(ProjectDir)SDK_RVA\\hook;$(ProjectDir)SDK_RVA\\minihook\\include;$(ProjectDir)SDK_RVA\\minihook\\src;..\\carrier')
edit('ai_docs/10_Trigger系统/注册器API与验证.md','首版提供 **bool 标量 trigger**，不是数值或块参数注册器。','本文的首版Bool部分是历史注册验证；当前已提供Bool、VALUE、VARIABLE三个模板，以及Array64操作数回调。')
edit('ai_docs/08_Effect系统/Scope与scoped操作数验证.md','下一步为数值/block Trigger 模板与 typed Trigger scope adapter；不能借用 Effect offset。','后续数值/block Trigger与typed scope adapter已实现并验证，见[typed模板](../10_Trigger系统/数值块模板与Scope适配.md)；仍不能借用Effect offset。')
edit('ai_docs/10_Trigger系统/数值块模板与Scope适配.md','以上是本轮所列输入的单人证据。格式化 tooltip、所有缺失/动态/temp/随机变量语义、完整前缀链、','以上是该轮单人证据。后续格式化tooltip与所列dynamic/temp优先级已验证，见[Tooltip生命周期](Tooltip与单人生命周期验证.md)与[动态/数组隔离](动态同名与数组隔离验证.md)。全部缺失/动态/temp/随机语义、完整前缀链、')
edit('ai_docs/10_Trigger系统/Tooltip与单人生命周期验证.md','尚未覆盖：全参数类型、动态变量同名冲突、数组/嵌套随机参数、所有前缀链与作用域存档、挂账、','该轮后续已补所列动态同名与原版数组隔离，见[动态/数组](动态同名与数组隔离验证.md)。仍未全面覆盖：全参数类型、全部动态冲突、数组/嵌套随机参数、所有前缀链与作用域存档、挂账、')

print('DOCS_RECONCILED_CORE_AND_HISTORY')
