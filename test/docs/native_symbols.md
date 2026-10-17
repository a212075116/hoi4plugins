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

## 证据

`test/reports/20261017_native_symbols/`保存修正前self/backup/exe3与修正后v2_*资料、`migration.json`；报告不纳入Git。
v2自扫去掉approve行仍与已提交资料逐字节相同；backup与修正前唯一差异是`var64.vartext=0x12bd550`。
未启动backup或exe3游戏，结论仅为离线候选与加载器接受性。
