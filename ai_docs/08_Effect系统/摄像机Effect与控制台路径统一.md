# 摄像机Effect与控制台路径统一

2026-10-12；用户要求effect_camera采用控制台camera同样检查/操作路径。对象为effect_camera.c，不更换其他摄像机实现。

## 修改

- 对象仍统一由Camera_GetObject定位，复用其全局槽、对象字段与高度内存可读检查。
- set_camera_height/add_camera_height不再直接调用RVA_CAM_SETH=0x12643F0，改为Camera_SetHeight，复用控制台已有平滑和忙时立即写入。
- 上下限继续复用Camera_GetLimits、真上下限约束与Smooth helper；删除平滑启动后将立即读到的旧上下限写回effect参数的操作。
- 日志区分target与immediate-readback，不把线程尚未完成时的旧高度/上下限写成最终结果。字面参数与动态表达式不被执行回读擅自改写。

## 联动实测发现

最初高度已经改变，但事件内部out->ok=0/访问异常；缩短事件名、去掉探针及补本地化均不能构成修复，不把这些阶段计为通过。
定位到Effect_BuildTooltip把RVA0x11DBC0的5参数扩容/拷贝函数按2参数调用，会使用不确定的源指针和拷贝长度。
原版AddStability tooltip反编译也显示它传5参数；改用已验证RVA0x129C10的3参数append(out,data,size)，删除后续手工重复拷贝。
因此联动修改effect_reg.c/h，不是为了新添功能；这里修复的是明确ABI错误，不代表此前Array64资源增长已归因。

另复现同一lowerlimit事件第二次执行只到50而非100：第一次平滑启动时旧代码读到50并回写了参数。
删除参数回写后，重复lower/upper事件均保持原始输入，控制台与Effect行为一致。

## 证据与边界

| 验证 | 结果 |
|---|---|
| 同输入受控C基线 | 7/13，旧RVA分支与异步参数回写不满足共享合约，exit1 |
| 修改版受控C | 13/13，exit0；NULL摄像机、共享setter拒绝、限幅和参数保留均覆盖 |
| 副本回滚 | 恢复原始源码字节/哈希，再得到与基线相同7/13、exit1 |
| 正式DLL游戏测试 | 9/9：set=950.25与控制台一致、500+49.75=549.75、上下限/重复输入、原生旧RVA调用0、相关解析错误0 |
| 回归 | Scope12/12及8回调；Trigger原生22/22 |

游戏测试等待平滑完成且持续稳定后才核对目标，最后恢复原摄像机高度和上下限；不更新战役存档。
这证明实际目标字段与公开事件执行，不冒充GUI像素/视觉验收；displayHeight仍可由游戏逐帧逼近目标。
测试localisation使用UTF-8 BOM的独立Camera test标签，未将它当正式中文界面视觉证明。
源码与ABI记录：test/reports/20261012_variable64_transaction/camera_unify/，最终native_final及build_final；早期失败原文保留。

本轮Current DLL归档由CURRENT_BUILD.json标识；旧Array64报告中的72704...是对应历史构建，不被覆盖或当作新构建验证。
资源增长原因、掉电/硬件持久性、多人和完整GUI仍未因此通过。
