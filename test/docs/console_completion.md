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

只读当前绑定PID的命令注册表；限已验证HOI4 1.19.3 PE指纹与x64布局。
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
本轮不改插件DLL、不重启游戏；只替换并重启外部helper。
证据在test/reports/20261013_console_completion。
