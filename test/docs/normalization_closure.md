# 源码规范化收尾核对

2026-10-14。生产源码和 DLL 保持第二十八批，本次补齐最终核对、所有权边界夹具和交付文档。
技术结论见[交付总结](../../ai_docs/01_工程与构建/源码规范化交付总结.md)。

## F1 可复现检查

项目根目录执行：

```powershell
python test/modules/effect/test_tooltip_ownership_boundary.py . test/reports/20261014_normalization_closure/manual
```

需要 VS2022 Community 的 vcvars64 与 cl。脚本提取实际 Effect_BuildTooltip，替换六个 RVA 回调；不进入游戏、不接触 Steam。
测试 11 个长度（0、1、15、16、32、149、150、191、399、400、511），各配四种 packed/fin 拥有/借用组合。
BASELINE、MODIFIED、ROLLBACK 均为：

```text
cases=44 failed=0 modeled_owned_temporaries_retained=32; mock-owned/borrowed contract only, not game allocator proof
```

退出码均 0，stderr 空。三个 Effect 源文件哈希完全一致，因为本次没有修改该函数。
32 是受控模型的 retained allocation 数，不是实际游戏泄漏数量或字节。
测试宿主回收模型分配；不能用模型证明游戏 producer 是 owned 或 borrowed，也不能据此调用游戏 free。
初次编译调用引号错误 exit1 已保留在报告 compile_error.json，改为 shell 字符串后成功。

## 证据与回滚

报告目录：`test/reports/20261014_normalization_closure/`。
final_verification.json 记录本次三态 stdout/stderr/status、源码清单与部署哈希，以及逐条目标核对。
执行现有 ROLLBACK.sh 恢复单独 SOURCE_MODIFIED 副本，恢复 ZIP 哈希与第二十八批 SOURCE_BASELINE 完全一致，再运行同一夹具。
当前生产源码保持原样，未以回滚副本覆盖工作区或正在加载的 DLL。

继续复用四个角色，目录为 `test/reports/20261012_variable64_transaction/`：

- MODIFIED_FILE.zip：源码、文档和证据归档。
- DIFF_FILE.patch：从原 BASELINE.zip 重建当前归档的二进制 patch。
- VERIFICATION.txt：JSON 证据台账；本次新增 normalization_closure，历史不覆盖。
- ROLLBACK.sh：对独立副本恢复原始字节；不直接操作用户存档。

## 完成与未知项

本次源码整理已交付；F1 是明确未证明的原生所有权调查，不宣称真实泄漏已解决，也不虚构 GUI / 多人 / 极端断电验收。
正常行为验证、已修正故障、保留原实现的未知合同三者必须分别解读。
历史第二十六批“尚不能完成”的原因是当时状态；当前 F2 / F3 已修正，F1 按上述边界保留。
