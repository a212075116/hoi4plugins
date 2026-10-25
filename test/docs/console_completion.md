# 外部控制台 Tab 指令名补全

2026-10-13。只补全首个指令词，不补参数值；不执行候选指令。

## 使用

- 输入set_并按Tab：列出实际匹配指令，自动补齐共同前缀。
- 唯一匹配：替换指令词并显示完成提示；后面的参数文本保留。
- 无匹配：提示且不改输入。
- 候选每行最多5个，窗口较窄时提前换行；按整个列表序号交替蔚蓝色/蓝绿色，恢复输入与日志原配色。
- 支持原版/插件实际注册的指令及别名，ASCII大小写不敏感、排序并去重。
- /help、/filter、/clear、/reconnect、/quit在本地补全，不查询游戏。
- 光标在参数区域时不处理；按Tab不是按回车，不自动提交候选。

## 候选来源与安全

只读当前绑定PID的命令注册表；主模块SHA对应`bindings/<SHA>.symbols`，要求资料批准与已声明的x64命令表布局。
通过ReadProcessMemory读取名称/别名，不写游戏内存，不执行help或候选，不依赖地图执行上下文。
注册表前后指针/容量/数量一致才采用结果；读取失败/变化重试有界，失败提示而不改输入。
首词最长128字节、名称/别名长度有界、表数量有界；输入仍不超过2048 UTF-8字节。
查询复用单个异步工作队列；同时只允许一个待处理补全。
输入修改、光标移动、历史切换或回车会使旧结果失效，不覆盖新编辑内容。
多人仅可查看名称；原有后端指令执行禁用不改变。无OS命令执行或权限提升。

## 已执行的检查

补全基础自测20/20、原有日志/队列自测17/17，均exit0。
实际PumpCompletion源码夹具9/9：单匹配、多匹配、参数保留、过期/光标移动、不匹配、错误与输入限额。
实机只读查询set_返回9个候选、exit0：

```text
set_cosmetic_tag
set_country_flag
set_debug_unit_controller
set_flag
set_global_flag
set_mud
set_ruling_party
set_var
set_weather
```

第一版使用help执行队列，当前前端状态返回“执行上下文不可用”，用户反馈没有补全。
保留失败记录后改为只读命令表，不能把第一版的自测通过记作实机通过。
修正后用户确认Tab正常；随后用户要求5个/行与交替配色，并确认最终显示符合要求。
CLI候选获取100/100通过；此为只读采集，不冒充100次实际键盘或多人执行验收。

## 自动检查

```powershell
hoi4_debug_console.exe --completion-self-test
hoi4_debug_console.exe --pid GAME_PID --complete set_
```

旧helper不支持新自测开关，BASELINE/ROLLBACK均usage、exit2；MODIFIED新自测20/20、exit0。
独立副本回滚恢复原helper哈希；该三态是功能入口对照，不是旧版通过补全测试。
上述2026-10-13交付不改插件DLL、不重启游戏，只替换并重启外部helper。
证据在test/reports/20261013_console_completion。

## 资料解析与缓存（2026-10-25）

- 每次游戏指令补全重新读取并解析`.symbols`，不缓存批准状态或`console.manager`；本地`/`指令补全不受影响。
- 文件非空、最多32768字节；拒绝NUL、非ASCII与非空白控制字符，支持LF/CRLF、首尾空白及末行无换行。
- 要求`schema=1`、`contract=symbols_v2`、映像SHA一致；键集合直接来自`symbol_catalog.h`，缺键、多键、重复键、空键值均拒绝。
- 全部批准位必须是0/1；`approve.core`与`approve.console`都为1才读取命令表。
- `console.manager`只接受完整无符号十进制或`0x`十六进制DWORD；拒绝符号、尾随垃圾、截断溢出、0和超出映像的指针槽。
- 仅缓存一个映像的SHA，身份键包括路径、卷/文件ID、大小、创建与修改时间；变化后重新哈希，哈希前后身份变化即拒绝。
- 资料改动即使保留原时间戳，下次查询也重新校验；撤销批准、删除、修复、重新批准均无需重启helper。
- 错误返回空候选和具体原因，不执行指令，不改变现有5个/行与交替配色。

这是补全端的结构、身份和许可检查，不代替插件原生加载器的代码指纹、组依赖和ABI验证。
SHA缓存依赖文件身份与元数据，不宣称能检测同一文件原位改写且刻意保留全部元数据；本轮不做防篡改保证。
插件本身的资料仍按既有启动加载规则生效，补全重新读资料不等于插件热重载。

```powershell
python test/modules/console/test_completion_profile.py --output test/reports/completion_profile
python test/modules/console/test_catalog_handles.py . test/reports/catalog_handles
```

本轮原生资料夹具49检查全通过，含保留资料时间戳的改地址/撤销批准、删除恢复、映像替换与非法输入。
命令表夹具35场景、1065检查通过；资料解析单独测，命令表夹具桩化绑定解析，不冒充真实进程读取。
Release控制台构建通过：日志/队列17/17、补全20/20、功能状态配色7检查通过。
本轮未启动游戏、未替换现用helper；构建及三态回滚证据在`test/reports/20261025_completion_profile/`。
