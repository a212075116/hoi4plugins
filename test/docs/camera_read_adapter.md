# 摄像机只读适配器测试

2026-10-14，Windows x64、Python + pefile。不需 Frida、IDA 或重编译 DLL；原插件函数不变。

## 使用

项目根目录离线核对：

```powershell
python test/tools/camera_read_adapter.py --image ../hoi4.exe --output test/reports/20261014_camera_adapter/offline_current.json
python test/tools/camera_read_adapter.py --image ../hoi4.exe.backup --output test/reports/20261014_camera_adapter/offline_backup.json
```

读正在运行的游戏，工具不负责启动/结束进程：

```powershell
$gamePid = (Get-Process hoi4).Id
python test/tools/camera_read_adapter.py --image ../hoi4.exe --pid $gamePid --output test/reports/20261014_camera_adapter/read.json
```

成功exit0，拒绝/失败exit2，原因写入JSON。NOT_IN_MAP是菜单下正确拒绝，不代表应重启。
未知profile和只验证过离线的backup在打开进程前拒绝运行时读取。
加载中OBJECT_MISSING可在确认同一进程仍活着后重试。

## 回归

```powershell
python test/modules/camera/test_camera_read_adapter.py ../hoi4.exe ../hoi4.exe.backup test/reports/20261014_camera_adapter/failure_matrix.json
```

29场景、0失败。实际适配器配合两份真实离线PE、受控内存及header/只读节变体，不冒充全部实机。
profile和leaf getter形式受限，未来内联/布局改变可明确拒绝，不能猜测调用。

## 本次证据

目录 `test/reports/20261014_camera_adapter/`：

- offline_current / offline_backup：动态表/getter，无预填RVA/虚槽。
- live_compare.json：CHI PID26524，20/20对照，目标高度310、上下限50～3000。
- normal_close.json：正常关闭并确认旧进程terminal，之后才启动菜单。
- live_menu.json：菜单PID71864确认CFrontEndIdler后NOT_IN_MAP。
- failure_matrix.json：29场景状态、期望及范围。
- getter_alias_observation / header_mismatch_observation / header_difference：初版保守拒绝同函数重复槽、重定位ImageBase，修正后加回归。

最初camera.c/h读取失败已纠正为实际camera_height.c/h；次级表破坏测试最初选了不满足四项过滤的短表，测试假设失败，改为合格次级表后通过。
错误来源保留，不记成通过。工具可用性三态、回滚、既有四角色更新见verification.json。
合同见[摄像机只读适配器](../../ai_docs/07_逆向能力/摄像机只读适配器.md)，生产DLL未改。
