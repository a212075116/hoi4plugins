# 成就模块接口回归

2026-10-14，第九批源码简化；变更仅为头文件、include及重复声明。

## 自动测试

从项目根目录执行：

```powershell
python test/modules/achievement/test_module_interfaces.py SOURCE_ROOT OUTPUT [BASELINE_ROOT]
```

`SOURCE_ROOT` 必须包含完整的 `src/` 树；`OUTPUT` 是独立输出目录。
可选 `BASELINE_ROOT` 检查入口及三个成就源文件的运行token未变化，允许本批include/声明调整。
驱动复用现有三个原生夹具，只改其输入根目录和报告位置；不连接游戏或Steam。
UI夹具内部 `MODIFIED` 标签表示测试当前生产包装器，不是本次三态标签；三态由三个独立源码根和输出目录区分。

| 同一输入 | BASELINE | MODIFIED | ROLLBACK |
|---|---|---|---|
| 资格兼容包装器/原生替身 | 31/31，exit 0 | 31/31，exit 0 | 31/31，exit 0 |
| 原版来源策略/打包边界 | 16/16，exit 0 | 16/16，exit 0 | 16/16，exit 0 |
| 图标/tooltip包装器及10000次更新 | 12/12，exit 0 | 12/12，exit 0 | 12/12，exit 0 |

三个夹具的执行stdout、stderr、退出状态三态一致；UI输出保留 `frame=1 visible=1` 和原有完整tooltip。
另外，修改版console/log回归17/17；八个接口的独立头文件类型检查通过；Debug、Release构建通过。
回滚源码ZIP及DLL副本均恢复原始哈希，工作区保留修改版。

## 报告与失败记录

报告目录：`test/reports/20261014_module_interfaces/`。
`baseline_state.json`、三态输出目录、`scope_guard.json`、`header_contract.json`、`rollback.json`、`final_verification.json`保存证据。
本批曾因删除声明时残留 `extern` 导致UI夹具编译C2159、exit 2，驱动exit 1；`first_attempt_error.json`保留原始失败。修正残留后同一夹具通过。

持续复用四角色：

- `test/reports/20261012_variable64_transaction/MODIFIED_FILE.zip`
- `test/reports/20261012_variable64_transaction/DIFF_FILE.patch`
- `test/reports/20261012_variable64_transaction/VERIFICATION.txt`
- `test/reports/20261012_variable64_transaction/ROLLBACK.sh`

`ROLLBACK.sh`接受 `*.module-interfaces.zip` 或 `*.module-interfaces.dll`独立副本，恢复本批基线。
完整包的binary patch重建和原始包回滚另行验证，不能把修改前源码包与最初项目包混为一谈。
新DLL只归档，部署版本清单不变；夹具不证明实际GUI、真人多人或真实Steam解锁。
接口职责见[成就模块接口与启动依赖](../../ai_docs/03_插件/成就模块接口与启动依赖.md)。
