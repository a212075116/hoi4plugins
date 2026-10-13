# 成就资格兼容：真实解锁与恢复验证

2026-10-13，HOI4 1.19.3 x64。间歇退出按用户要求延后，不作为本阶段前置。

## 已观察到的真实结果

自动以-start_tag=CHI启动独立非铁人局，debug开启，资格校验和标志不通过。
资格补齐后：definitions293、pending10、completed254、excluded29。
执行原版annex all，正常模拟时间从raw60759371到60760115，相差744小时，即本次一个游戏月。
原生happened通过ID254 its_all_coming_together，日志19:00:56.548记录调用原版完成函数。
之后pending9、completed255、excluded29；用户明确确认看到了Steam该成就解锁提示。
这里的平台确认来源是用户，不冒充工具看到了GUI；没有捕获到首次提交的Steam回调包。
ID255 the_coast_is_clear仍不满足1945年日期；ID256 a_fullmetal_brotherhood仍不满足法西斯政体，均pending。
账号原有254个已完成项，包含ID264，因此不使用ID264证明首次解锁。
没有直接Steam赠送、ResetAllStats或ClearAchievement；用户授权真实条件触发账号解锁。

## 实现与边界

- 保留原版定义来源阶段，只用游戏根目录common/achievements.txt。
- 补齐总资格Getter、新局候选、存档候选ID恢复、正常运行检查的原版vanilla部分。
- 不清空全局debug、不置A3调试模拟、不修改铁人模式位。
- 铁人条件仅在原版possible评价的线程局部上下文放宽，其他possible和全部happened保留。
- 原生资格已通过时不重复补执行；已完成项使用原生平台状态分类，避免重复提交。
- 多人、加载中、平台metadata/接口未就绪、模拟调试模式不补执行。
- 使用实际SteamContext stats就绪信息，不把存档中的A1资格位当作平台或会话ready。
- 独立mod自定义成就目录仍走原生逻辑，完整性校验不绕过。
- 版本/安装失败时保持原生路径；不宣称其他版本已支持。

## 受控测试

生产wrapper源码加mock原生依赖31/31、exit0；不冒充真实多人/离线测试。
覆盖单人环境放行、多人拒绝、平台未就绪、加载/模拟拒绝、positive/negative possible、
铁人条件上下文隔离、真实happened不放宽、已完成不重复、候选ID同步、保存IDs恢复、空IDs待重建、SEH上下文复原。

```powershell
python test/modules/achievement/verify_compat_native_fixture.py
```

## 保存与恢复

保存到专用codex_achievement_CHI_20261013_verified.hoi4；专用保存/读档测试前后39个已有存档哈希未变化。
首次恢复发现A1被非铁人存档恢复为0，第一版误用它导致active0、候选0；保留失败证据后修正。
修正版本重启时平台已完成数255；载入专用存档后A1仍0，但active1，pending9/completed255/excluded29保持。
保存恢复已观察到候选恢复与已完成状态保持；暂停状态下ticks0不冒充恢复后运行压力测试。
真实恢复后的长时间继续运行、平台重连、模式切换、更多成就组合与多人仍需扩展。
文件/DLL回滚不撤销Steam账号成就，ID254不会被重置。

## 测试驱动注意事项

部分原版指令执行后没有填写ok位，CLI可能exit1；不能只凭它宣布动作失败或成功。
本次annex all返回status0/ok0且无消息，后续通过真实条件、完成记录和账号提示确认该流程结果。
pause_in_hours返回“Game will pause after ... hours.”但ok0；原生gamespeed/auto_unpause正常返回ok1。
第一版驱动误把这些返回当失败，游戏没有被杀；修正仅识别明确的原版返回形式，不吞掉Unknown command或传输错误。
没有setgamedate/add_months跳日期；通过真实模拟并读取raw时间差确认744小时。

## 证据

test/reports/20261013_achievement_eligibility下含before/after候选、真实解锁接受记录、
专用存档、原有存档哈希、恢复首次失败/修正成功记录、构建、夹具及三态回滚记录。
[Steam官方说明](https://partner.steamgames.com/doc/api/isteamuserstats)：服务器持久保存/通知涉及StoreStats；
不能仅凭管理器列表改变就宣称平台已确认。本次还具有用户实际平台提示确认。
