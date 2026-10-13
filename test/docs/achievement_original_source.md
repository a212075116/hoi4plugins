# 原版成就定义来源：阶段测试

2026-10-13，限定HOI4 1.19.3指纹。本文记录原版来源阶段，当时资格放行尚未开启。
后续资格已接通并实际解锁ID254，见[资格兼容测试](achievement_eligibility.md)。

## 实现边界

- 始终读取游戏根目录common/achievements.txt；公开同名mod覆盖不参与原版定义加载。
- 原版文件通过Win32读取，封装成单文件内存ZIP，放到私有VFS命名空间。
- 仅原版加载器的线程局部上下文重定向精确路径；其他文件、独立mod自定义目录照常走原生流程。
- 不改铁人位、全局调试标志、真实possible/happened条件或Steam账号状态。
- 私有路径冲突/原版空或超过16MiB/读取或挂载失败时报告失败，不自动采用mod定义。
- 内存快照仅在本次进程有效；游戏原版文件变化后应重启。

## 已执行

生产头文件精确匹配、上下文与大小边界16/16，exit0。
内存ZIP由独立Python zipfile验证CRC、唯一条目和二进制内容，成功。
真实VFS非空公开覆盖夹具7/7，exit0：公共读取确实变成夹具，私有读取仍与原版哈希相同。
夹具在finally移除；普通公共来源恢复；manager168字节前后哈希相同。
这个夹具检查没有在覆盖后重新运行原生定义解析器，不能冒充完整“带该mod启动”的验证。
空覆盖启动、错误/重载/进程退出生命周期抗压仍需要继续验证。
实机命令已返回installed=1 mounted=1 loads=1 redirects=1 failures=0 definitions=293。

## 间歇退出

本阶段用户报告一次自行退出，未见新游戏崩溃目录或匹配Windows应用错误事件。
用户补充此现象早期插件即存在、间歇发生；不能认定仅是新成就代码或Frida倒计时。
第一轮曾附加Frida做临时VFS夹具验证；无证据证明它与退出有因果关系。
随后观察轮不附加Frida，Explorer父进程、in_job=false、没有超时kill；180秒结束时STILL_ACTIVE=259。
用户这轮正常入图并完成CHI操作；这是单轮存活证据，不是稳定性验收通过。
后续用户明确要求该问题延后，不作为成就主线前置；不能凭概率现象宣称修复。

## 命令

```text
achievementsource
achievementstatus
```

```powershell
python test/modules/achievement/verify_original_source.py
```

原生VFS脚本仅用于独立测试局，临时更换公开路径可见内容，不能用于正式战役或多人。
证据目录：test/reports/20261013_achievement_source。
CHI操作按[端到端流程](achievement_chi_annex_flow.md)，后续阶段已经接通并记录单例解锁。
