# 第六批遗留实现与注册胶水回归

2026-10-14。测试只操作源码副本和夹具，不附加游戏、不执行游戏指令、不修改存档或成就。

## 入口引用证据

补充目录 `test/reports/20261014_var64_cleanup/`保存原始源码zip、reachability_baseline.json和scope_guard.json。
10个被删除static函数的生产引用全部落在删除闭包内部，没有有效注册或hook入口；8个配套状态/常量也只在该闭包中使用。
保持全部有效处理函数和公开SDK头文件，不能单凭名字带Unused就删除。
原保留static函数、arithmetic hook installer定义均不变；注册公有函数另做下面的行为对照。

## 实际注册实现三态对照

```powershell
python test/modules/effect/test_var64_registration_glue.py src/plugin/SDK_RVA/variable64/variable64.c OUTPUT_DIR
```

OUTPUT_DIR独立，依赖VS2022 Community x64工具链。
夹具编译真实EFF_DEF宏/7个声明、真实Effect_RegistryRegisterAll与真实Var64_RegisterEffects；底层registry、game image、factory对象及安装操作为模型。
固定seed20261017（不是执行日期），共27268组输入，包含7项state全部3^7组合与1024随机组合。
观察7个factory标记/顺序、name/description/locKey、state/token、entryVt[0]/其他slot，以及supportedScopes/exec/tooltip和hooks调用顺序。
BASELINE、MODIFIED、ROLLBACK同输入的stdout逐字节一致、stderr为空、exit0；固定factory顺序和返回数量检查也通过。
初版夹具把SDK_RVA路径定位到src而非plugin，启动失败exit1；路径修正记录保留，不修改生产代码来适配该错误。

## 连带回归

三态运行十套既有检查：身份8/8、三槽2049/2049、算术10676/10676、语言名6/6、ROOT操作数、setter债务9/9。
文本16696条、字段/桥接31168条、解码21304条、债务10083步也重跑，输出与轨迹保持。
身份夹具仅在旧源码存在名字表查询函数时提取，现代路径仍验证真实三槽身份，不另造替代生产算法。
源码引用/模型对照不能代替实际游戏、原生对象分配器、GUI或外部调试器兼容验收。

## 构建与回滚

Debug/Release解决方案构建通过。
源码包、源码文件、DLL分别在独立副本上回滚到本轮基线字节/哈希，恢复源码重新编译并重跑同输入。
修改版保留在项目与归档；未覆盖游戏根部署文件，也未重启游戏。
正式四角色继续使用 `test/reports/20261012_variable64_transaction/` 下MODIFIED_FILE.zip、DIFF_FILE.patch、VERIFICATION.txt与ROLLBACK.sh。
