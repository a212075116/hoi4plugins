# 国家选择界面的成就图标与提示

2026-10-13，限定已验证HOI4 1.19.3指纹；用户确认图标和悬浮文字都正确。

## 当前行为

只匹配国家选择前端的enabled_achievement_icons。
在原生前端更新完成后，使该图标可见并设为允许成就的第1帧。
悬浮提示完整替换为：[hoi4plugins]：成就允许解锁！
其他名称的控件仍使用原版tooltip；图标不存在或接口不可读时跳过补写。
原版interface/frontendgamesetupview.gui和纹理均不修改。
该显示是用户指定的固定提示，不会解除后端的多人、平台未就绪、真实possible/happened限制。
UI Hook仅在成就兼容模块成功安装且版本匹配时安装；不支持版本/失败保留原生行为。

## 定位与实现

原版GUI中图标名位于frontendgamesetupview.gui第2278行。
原生前端更新RVA0x1CDA120在bottom容器查找该图标并按资格结果设置帧。
原生tooltip路由RVA0x1CD4570按控件名称生成原版资格说明。
achievement_ui.c分别Hook这两个入口；更新返回值保留，tooltip只覆盖精确同名控件。
使用原版字符串分配函数0x129CA0写入UTF-8，不依赖中文源码的本机ANSI编码。
原函数指针在批量启用前发布；创建/启用失败清理本模块Hook，不影响既有资格模块。

## 已执行的验证

| 三态夹具 | 结果 | exit |
|---|---|---|
| BASELINE | 模拟原生旧路径：frame3、hidden、原资格提示；8/12 | 1 |
| MODIFIED | frame1、visible、目标UTF-8提示；12/12 | 0 |
| ROLLBACK | 恢复模拟旧路径；8/12 | 1 |

夹具包含生产wrapper源码，但native widget/旧路径依赖是mock，不冒充实际渲染截图。
精确名称、其他tooltip隔离、空查找、返回值保持与10000次更新已验证。
独立核对输出UTF-8码点与用户原文完全相同。
实机插件日志确认AchievementUi_Install与注册成功；用户进入国家选择并确认图标与tooltip正确。
启动前主菜单的外部命令请求曾因执行上下文不可用exit3；不把它记作Unknown command或UI失败。
回滚在独立DLL/源码包副本上执行，哈希与基线一致；游戏保留已部署修改版，不为UI回滚再打断用户。
原版GUI SHA256仍为829f1bb6002021dbe644706a30a31470c680e4fa5087f1c5b5c6ad762cce4494。

## 辅助命令与证据

进入可执行外部命令的地图后，achievementui/achui读取安装、更新和tooltip计数。
该命令只读；主菜单上下文不可用不是安装失败。

```powershell
python test/modules/achievement/verify_ui_fixture.py BASELINE
python test/modules/achievement/verify_ui_fixture.py MODIFIED
python test/modules/achievement/verify_ui_fixture.py ROLLBACK
```

证据位于test/reports/20261013_achievement_ui，包括原版GUI副本、原生反编译、构建、夹具、用户视觉确认及回滚记录。
成就后端与真实解锁记录见[资格兼容测试](achievement_eligibility.md)。
