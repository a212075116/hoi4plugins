# 第二批variable64源码重构回归

2026-10-13。目标：十进制/显示规则提取、重复侧槽命名合并，保持旧行为。
本测试不启动或附加游戏，不执行游戏命令，不操作存档和成就。

## 固定输入三态对照

从项目根运行，OUTPUT_DIR使用独立目录：

```powershell
python test/modules/effect/test_var64_text_refactor.py src/plugin/SDK_RVA/variable64/variable64.c OUTPUT_DIR
```

需要VS2022 Community原生x64工具链。旧版单文件源码提取真实函数；新版包含三个真实private模块，不在夹具中重新实现生产算法。
输入固定种子20261013：共16696条，含4096条随机格式修饰符组合。
覆盖正/负/零、受支持整数边界、小数正负、精度、百分比、K/M、颜色/正号及修饰符顺序。
名称覆盖空/NULL、15/16/31/32/33/40/41字节边界（33字节主名在输出容量足够时仍合法）、输出不足、成功与失败时的完整缓冲内容。
对96字节显示缓冲与64字节名称缓冲全部编码后比较，包含终止零和未写区域，不只比较可见前缀。

BASELINE、MODIFIED、ROLLBACK：同输入、16696条输出逐字节相同，stdout SHA-256相同、stderr为空、exit0。
三态另有9/9固定期望检查，stdout为 `9/9 text/name sanity checks`、exit0。
新测试最初把函数调用误认作定义，修正为锚定static定义；最初失败编译记录保留，不属于生产功能失败。

## 既有数值回归

下列脚本均以SOURCE_FILE和独立OUTPUT_DIR调用，三态各执行一次：

| 脚本 | 覆盖/结果 |
|---|---|
| `test_var64_identity.py` | 8/8：容器身份、缺主槽、假标记、长名、冲突桶、无写入 |
| `test_var64_stored_raw.py` | 2049/2049：三槽解码、边界与异常溢出 metadata |
| `test_var64_raw_math.py` | 10676/10676：饱和加减与定点乘除Python整数oracle |
| `test_var64_language_name.py` | 6/6：SSO/借用长名字段、39/40字节边界 |
| `test_var64_scoped_operand.py` | ROOT 2.5操作数、正确descriptor offset及其他容器不变 |
| `test_setter_debt_native.py` | 9/9：升级/降级、清债务与失败setter保持旧状态 |

```powershell
python test/modules/effect/test_var64_identity.py SOURCE_FILE OUTPUT_DIR
python test/modules/effect/test_var64_stored_raw.py SOURCE_FILE OUTPUT_DIR
python test/modules/effect/test_var64_raw_math.py SOURCE_FILE OUTPUT_DIR
python test/modules/effect/test_var64_language_name.py SOURCE_FILE OUTPUT_DIR
python test/modules/effect/test_var64_scoped_operand.py SOURCE_FILE OUTPUT_DIR
python test/modules/effect/test_setter_debt_native.py SOURCE_FILE OUTPUT_DIR
```

涉及游戏内存与原生调用的依赖为夹具模型，不是实机scope或GUI验收。
身份/解码夹具已兼容旧单文件与新private名称模块；修正依赖读取时的脚本缩进错误，失败stderr保留。

## 回滚、构建与证据

原四角色继续使用 `test/reports/20261012_variable64_transaction/` 的MODIFIED_FILE.zip、DIFF_FILE.patch、VERIFICATION.txt和ROLLBACK.sh。
新补充证据在 `test/reports/20261013_var64_refactor/`：源码基线、改版、恢复副本、三态inputs/stdout/stderr、JSON结果与构建日志。
源包和DLL分别在独立副本上恢复到本轮基线，字节/哈希一致；恢复源码重新编译并重复同输入测试。
修改版仍保留在项目与归档中，不用回滚副本覆盖生产源码。
Debug/Release构建通过；本轮没有部署新DLL，CURRENT_BUILD继续代表游戏根已部署版本。
