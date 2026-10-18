# 第三轮原生符号目录测试

2026-10-17。合同见[原生符号目录](../../ai_docs/07_逆向能力/原生符号目录.md)。

## 迁移候选

项目根，依赖Python pefile/capstone/numpy；每映像约140-160秒（字符串引用扫描占大半）：

```powershell
python test/tools/migrate_native_symbols.py --baseline-image ../hoi4.exe --image ../hoi4.exe --output-directory test/reports/20261017_native_symbols/v2_self --rescan
python test/tools/migrate_native_symbols.py --baseline-image ../hoi4.exe --image ../hoi4.exe.backup --output-directory test/reports/20261017_native_symbols/v2_backup
```

输出`<SHA>.symbols`和`migration.json`。自扫结果去掉approve行后应与`bindings/`中已提交资料逐字节相同。
不同SHA永远全组禁用；不要直接复制到`bindings/`部署。

## 原生夹具

VS2022 x64 Developer Command Prompt，项目根：

```bat
cl /nologo /EHsc /std:c++17 /O2 test/modules/adapter/native_symbols_fixture.cpp /Fe:test/reports/20261017_native_symbols/sym.exe /Fo:test/reports/20261017_native_symbols/sym.obj /link bcrypt.lib shell32.lib
test\reports\20261017_native_symbols\sym.exe "D:\SteamLibrary\steamapps\common\Hearts of Iron IV\hoi4.exe" bindings\7dc947be34970da1e1c787bcddbe7f62b610ff258aebf8f06aa8b348f3a031d5.symbols
test\reports\20261017_native_symbols\sym.exe "D:\SteamLibrary\steamapps\common\Hearts of Iron IV\hoi4.exe.backup" test\reports\20261017_native_symbols\v2_backup\<SHA>.symbols --accept
```

默认模式：实际`native_adapter.cpp`与`native_symbols.inc`在当前映像及重定位受控内存中23检查，覆盖缺资料、批准传播、
registry依赖、指纹/节/格式/key集合/身份/NUL拒绝、loaded槽与代码被改、恢复后一致、未发布API关闭。
`--accept`：把临时副本全部批准位改为1，只报告生产加载器逐组结果；不修改输入资料，退出码0表示全部组就绪。

## 本次结果

| 运行 | 结果 |
|---|---|
| 默认夹具，当前映像 | 23/23 |
| 自扫`--accept` | 10/10组 |
| backup`--accept` | 10/10组（RIP屏蔽修正前8/10，`var64.vartext:RVA_INVALID`与依赖array64） |
| exe3`--accept` | 2/10组，预期失败 |

exe3的`diag.gamestate_vt2`静态与运行时都报RTTI_TABLE_MISSING；`achievement.iron`静态报表过短，运行时该组先因`flag_log`未解析关闭。
同时回归改动涉及的Python夹具：camera启动门、console bootstrap/scheduler/字符串、effect var64/array64、gamedate三项、hook两项均exit 0。
`achievement/verify_ui_fixture.py`为8/12，第二轮代码stash后同为8/12，是既有失败，不属本轮回归。
Windows控制台GBK下部分夹具打印报UnicodeEncodeError，设`PYTHONIOENCODING=utf-8`后正常，不是功能失败。

## 一键迁移（第四轮）

```powershell
python test/tools/migrate_image.py --image ../hoi4.exe.backup --output-directory test/reports/20261017_migrate_image/backup --symbols-fixture <sym.exe>
```

默认基准为`../hoi4.exe`；同SHA用`--rescan`自扫。三映像并行约2分钟（第五轮缓存后；此前约12.5分钟）。
自扫`.symbols`、`.registry`去掉批准行后与已提交逐字节相同；backup symbols 27/27、registry 23/23、token 10766，`--accept` 10/10。

## 实机驱动

```powershell
python test/modules/adapter/live_bindings_check.py --exe ../hoi4.exe --output test/reports/20261017_live/current
```

关闭已有游戏（先CloseMainWindow，超时才强杀）、把功能日志移为`.log.prev`、以`-start_tag=CHI`启动、等`Launching SINGLEPLAYER-game`后30秒，
经`hoi4_debug_console.exe --pid --command`执行四条只读命令，正常关闭，输出`live.json`与功能日志副本。
功能日志`adapter.identity`不等于映像SHA即判失败；载体只在宿主名为`hoi4.exe`时加载插件，其他文件名会表现为“无日志”。

| 运行 | 结果 |
|---|---|
| 当前映像+新构建 | 35秒进图，36项全可用，四命令exit 0，正常关闭 |
| backup以原名启动 | 40秒进图但插件未加载（载体按名拒绝），作为驱动修正依据保留 |
| backup换名为hoi4.exe | 38秒进图，除有意关闭的摄像机写入4项外全可用，token 10766，摄像机310/50/3000，正常关闭；exe已按SHA复原 |

## 字段偏移检查（第五轮）

```powershell
python test/tools/check_native_fields.py --image ../hoi4.exe.backup --migration test/reports/20261018_migrate_image/backup/migration.json --output test/reports/20261018_fields/backup.json
```

`migrate_image.py`已自动运行并写入`migration.json`的`fields`；单独运行约3秒。自扫50一致、4无见证；backup 47一致、3多数一致；exe3 7项移动。
exe3摄像机指针`0x728`另由`camera_read_adapter_core.find_getter`在槽36/37独立确认。

速度回归：缓存索引与旧扫描在7个真实目标上引用集合完全相同；首版按位置取前N个锚点时`achievement.vector_push`退化为未解析，
跨步加按函数长度排序后恢复；`param.get`在backup出现10:1，以多数票加复核标记恢复。最终三映像126秒，资料与第四轮逐字节相同。

## 证据

`test/reports/20261017_native_symbols/`保存修正前self/backup/exe3与修正后v2_*资料、`migration.json`；报告不纳入Git。
v2自扫去掉approve行仍与已提交资料逐字节相同；backup与修正前唯一差异是`var64.vartext=0x12bd550`。
`test/reports/20261017_migrate_image/`保存第四轮三映像资料与报告；`test/reports/20261017_live/`保存实机`live.json`、功能日志、部署前DLL及backup测试资料。
backup只做了启动、注册与只读命令实机；exe3未启动。脚本行为与摄像机写入未在backup上验证。
