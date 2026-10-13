# 第五批债务生命周期回归

2026-10-14。证据目录沿用本批启动时的 `20261013_var64_debt_refactor`，不改动已记录的路径。
测试不附加游戏、不执行游戏命令，不改存档或成就。

## 固定生命周期输入与独立oracle

```powershell
python test/modules/effect/test_var64_debt_lifecycle.py src/plugin/SDK_RVA/variable64/variable64.c OUTPUT_DIR
```

OUTPUT_DIR为独立目录，依赖VS2022 Community x64编译器。
旧版提取真实债务块，新版包含真实debt.inc；container解析和Heap调用使用受控模型。
Heap模型每次成功扩容都移动内存，复制旧内容并清零新增区域；可按输入让初次分配或扩容失败。
结构大小72字节、关键字段offset先由C夹具确认；Python独立维护字节数组，计算记录内容和FNV64，而不是调用生产算法作为期望。

固定种子20261016只是seed，总计10083步，含10000步随机生命周期操作。
观察返回index、容量、active数量、表是否移动、container/GetProcessHeap/Alloc/ReAlloc调用次数、整表字节哈希与日志。
BASELINE、MODIFIED、ROLLBACK各10083/10083符合oracle；同输入stdout逐字节一致、stderr为空、exit0。

## 已覆盖路径

- 无表/NULL name的Find不解析container；NULL name的New仍按旧顺序解析。
- 不同container中同名记录互不匹配，reset不清其他owner。
- 直接重复New不去重，Find返回第一条active匹配。
- 初始64槽、填满、扩容失败保持旧表、重试成功、继续翻倍。
- 扩容移动后原记录字节保留、新区域清零。
- Clear(NULL)、无效index、清理后复用首个inactive槽。
- name尾部、旧container和padding的旧保留行为，不把清理改成全结构memset。
- 数值清零、inactive脏值初始化、失败日志和容量不收缩。

## 连带回归与恢复

三态运行九套既有回归：身份8/8、三槽2049/2049、算术10676/10676、语言名6/6、ROOT操作数、setter债务9/9。
文本16696条、字段/桥接31168条、解码/查询路径21304条也重跑，输出/轨迹一致。
setter夹具支持展开debt.inc后提取真实函数和记录类型，旧版主文件仍可用。
身份夹具原来用DEBT_MAX宏定位函数块结尾，拆分后失败；已改为提取明确的函数定义，失败stderr保留，未为适配夹具改变生产代码。
涉及游戏依赖的夹具仍是模型，不等同于实机分配器、读档生命周期或多人验收。

Debug/Release完整解决方案构建通过；源码包、源码文件、DLL的独立副本恢复到本轮原始字节/哈希，恢复源码重编译并重跑同输入。
修改版保留，不用恢复副本覆盖项目；未部署新DLL、未重启游戏。
补充报告：`test/reports/20261013_var64_debt_refactor/`。
四角色继续使用 `test/reports/20261012_variable64_transaction/` 中MODIFIED_FILE.zip、DIFF_FILE.patch、VERIFICATION.txt与ROLLBACK.sh。
