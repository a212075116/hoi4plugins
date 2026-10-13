# 第三批名称字段与语言桥接回归

2026-10-13。验证共享目标名称复制与原生语言桥接职责拆分；不附加、不启动、不执行游戏命令。

## 三态固定输入

从项目根执行，OUTPUT_DIR使用独立目录：

```powershell
python test/modules/effect/test_var64_name_fields.py src/plugin/SDK_RVA/variable64/variable64.c OUTPUT_DIR
```

VS2022 Community x64编译器编译真实目标/操作数读取函数及完整语言桥接块。
旧版从主文件提取语言桥接块；新版包含真实name_field头文件及language.inc，不复制一套生产算法到模型里。
Win32可读性、模块基址、原生解析/append、hook安装依赖为受控模型。

固定种子20261014，不是测试执行日期。总计31168条输入，含2048条随机名称读取组合。
记录内容包括整个64字节输出、源实例是否变化、原生输出参数状态、逐次可读检查大小/结果、失败日志及桥接回退/追加轨迹。
BASELINE、MODIFIED、ROLLBACK三态inputs/stdout逐字节相同、stderr为空、exit0。
三态另有10/10固定期望检查，stdout为 `10/10 field/bridge sanity checks`，exit0。

## 覆盖点

- 空/NULL输入、NULL输出、容量7/8/39/40/41/64、SSO15与指针字段。
- 名称15/16/31/32/33/34/40/41字节、异常capacity元数据、不可读字段或数据。
- 数据只可读size而不可读size+1时，两条目标路径仍保持原有差别。
- indexed/compound拒绝及日志；literal操作数拒绝；失败时是否清输出。
- 原生参数/地址位置不可读时，输出清零、返回值和失败顺序。
- 本地化按frac/main/high顺序解析；借用字段size/capacity/终止零。
- 名称过长、无原handler、无ctx/out、depth、坏标记、非整槽数值的原版回退。
- prefix保留并append，不把追加改成覆盖；append/out不可读时保持原行为。
- hook安装成功、重复安装不重复调用、失败后未标记安装、无模块不安装。

新夹具最初没有允许已知语言hook目标可读，安装检查因此失败6/10；修正模型后10/10，失败stdout及exit1保留。
该失败不是靠改动生产安装逻辑修复的。

## 既有回归与恢复

三态重复执行身份8/8、三槽解码2049/2049、算术10676/10676、语言名称6/6、ROOT操作数、setter债务9/9，以及上一批16696条文本/侧槽命名对照。
语言名称历史夹具支持展开language.inc，旧版主文件仍可使用；其余算法不改写。
这些夹具不等于实机scope、原生分配器或视觉验收。

Debug/Release解决方案构建通过，源码包/源码文件/DLL独立副本恢复到本轮原始哈希，恢复源码再编译并重跑相同输入。
修改版源码与构建产物保留；没有用恢复副本覆盖项目。
未部署新DLL、未关闭游戏；CURRENT_BUILD继续代表当前游戏根已部署版本。

补充报告：`test/reports/20261013_var64_fields_refactor/`。
正式四角色仍是 `test/reports/20261012_variable64_transaction/` 的MODIFIED_FILE.zip、DIFF_FILE.patch、VERIFICATION.txt和ROLLBACK.sh。
