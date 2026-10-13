# 注册接口三态回归

2026-10-14，第十批源码简化。入口声明收拢，不改变注册函数实现。

## 新增Array64注册夹具

从项目根目录执行：

```powershell
python test/modules/effect/test_array64_registration.py SOURCE_ROOT OUTPUT
```

`SOURCE_ROOT`需包含完整 `src/`；`OUTPUT`为独立输出目录。
夹具提取真实 `Array64_RegisterEffects`、`Array64_RegisterTriggers`，使用真实Effect/Trigger类型声明。
原生映像、factory/exec/tooltip函数及注册器调用由受控替身提供，不调用游戏。
4100组包含：未就绪、无映像、4096组已有状态/失败掩码、Trigger成功与失败。
检查注册计数、已有OK跳过、名称、parser、虚表位置、模板与回调绑定；不证明原生factory执行或持久化。

## 匹配三态结果

| 检查 | BASELINE | MODIFIED | ROLLBACK |
|---|---|---|---|
| Array64生产注册函数 | 4100/4100 | 4100/4100 | 4100/4100 |
| scalar64注册映射/顺序夹具 | 27268组 | 27268组 | 27268组 |
| Bool Trigger注册器 | 22/22 | 22/22 | 22/22 |
| typed Trigger | 27/27 | 27/27 | 27/27 |
| 摄像机受控adapter | 13/13 | 13/13 | 13/13 |
| console/log行为 | 17/17 | 17/17 | 17/17 |

同输入执行stdout、stderr及退出状态一致，全部exit 0；编译日志单独保留。
scalar64输入文件哈希和完整stdout另保存，不能只比较通过数量。
八个公开入口的重复包含/类型检查及Debug/Release整套构建通过。
独立修改版源码包、DLL副本经回滚后与本批基线字节/哈希一致；工作区仍保留修改版。

## 记录与限制

本批报告：`test/reports/20261014_registration_interfaces/`，包含基线、三态夹具、scope guard、构建、回滚与最终验证。
初版夹具误用只能提取static函数的旧助手，exit 1；已改为锚定公开定义的提取器，错误来源及修正保存在 `extractor_error.json`。没有因此改生产函数。

继续复用 `test/reports/20261012_variable64_transaction/` 下的四角色：
`MODIFIED_FILE.zip`、`DIFF_FILE.patch`、`VERIFICATION.txt`、`ROLLBACK.sh`。
回滚脚本对 `*.registration-interfaces.zip` 和 `*.registration-interfaces.dll`副本恢复本批基线。
完整归档另验证binary patch重建与最初项目包回滚。

不部署DLL，不启动游戏，不把夹具当作实际日期执行、真实渲染、Steam解锁或真人多人测试。
用户已允许自行启动并通过 `-start_tag=TAG` 自动开局；需要实机时采用独立测试局，不以重构夹具代替实机结论。
实现职责见[注册接口与入口依赖](../../ai_docs/03_插件/注册接口与入口依赖.md)。
