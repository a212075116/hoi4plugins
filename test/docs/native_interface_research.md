# 原生接口与跨版本定位研究

2026-10-14。研究工具与静态可行性验证，不是已部署新功能。

项目根目录执行（Python 需安装 pefile）：

```powershell
python test/tools/research_native_interfaces.py --image ../hoi4.exe --image ../hoi4.exe.backup --output test/reports/20261014_interface_research/rtti_two_images.json
```

工具读取导出名、RTTI 类型名、COL image-relative 结构，以及只读段内 COL 指针引用。
候选前四项须指向该映像可执行节；不推导表长，会漏掉更短/无 RTTI 等情况。
保存完整 SHA；资源版本 1.0.0.0 不能辨识具体发行版本。
结构匹配不证明对象有效、签名兼容，不能直接把报告当成 hook 安装地址。

报告 `test/reports/20261014_interface_research/` 中，rtti_two_images.json 保存候选/导出/同名配对，pdxsdk.json 保存 SDK 检查。
文档原始副本与验证也保留在报告目录，旧“没有”及 RTTI 宽度错误不再作为当前结论。
本次没启动游戏，没改生产源码或 DLL，没有宣称跨版本实机功能验收。
结论见[接口复核](../../ai_docs/07_逆向能力/有没有官方接口.md)、[适配层](../../ai_docs/07_逆向能力/跨版本定位与适配层.md)。
