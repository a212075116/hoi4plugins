# gamedate 模块测试脚本

> 对应源码 `src/plugin/SDK_RVA/gamedate/`。
> 先看《README.md》里的硬规则，再动这里的脚本。

## 探针（.js，放进程里执行）

| 文件 | 暴露的方法 | 作用 |
|---|---|---|
| `game_date_read.js` | `getDate` `peek(off,n)` `setRaw(v)` `find(v,lo,hi)` `poke(off,v)` | **主力探针**：读/写日期真源、dump 内存窗口 |
| `game_state_scan.js` | `peek` `find` `findHeap(v,max)` | 扫 CGameState 窗口与堆，找某个值出现的位置 |
| `compare_two_dates.js` | `both(addr)` | 同一时刻对照 CGameState 与另一个地址的值 |
| `find_date_structures.js` | `scan(max)` | 按「[p-8] 是月天数、[p] 是年」特征找日期结构 |
| `find_date_structures_narrow.js` | `scan(max)` | 上面的窄化版（再加 [p+4] 范围约束） |
| `memory_around_address.js` | `around(addr,前,后)` `vtOf` `read` | 读任意绝对地址周围的结构 |
| `reverse_pointer_lookup.js` | `ptrsTo(target)` `statics(target)` | 反向找「谁指向这个地址」（CE 的 pointer scan） |
| `game_date_statistics.js` | `install` `stat` | hook 日期相关函数，统计调用次数 |

## 运行脚本（.py）

### 最常用

| 文件 | 用法 | 作用 |
|---|---|---|
| `read_game_date_fields.py` | 无参 | **读当前日期**：raw + 派生五字段 + `+0x4C0` |
| `set_game_date_with_argument.py` | `503.7.8.0` | **设日期**（走插件的 `setgamedate` 指令，会触发界面刷新） |
| `test_add_time_commands.py` | 无参 | 测四个加减指令（年/月/日/小时，含负数） |
| `test_add_time_effects.py` | 无参 | 测四个加减 effect（靠 `event zzdatetest.N` 触发） |
| `ensure_time_running.py` | 无参 | 确认游戏在跑（不动就调 `auto_unpause`） |
| `force_time_running.py` | 无参 | 反复尝试直到日期真的开始走 |

### 暂停 / 时间流逝相关

| 文件 | 作用 |
|---|---|
| `check_pause_state.py` | 隔 3 秒读两次日期，判断是否暂停 |
| `toggle_auto_unpause_1/2/3.py` | 发 `auto_unpause`（**它是开关**，看返回值） |
| `resume_time_flow.py` | 恢复时间流逝 |
| `read_state_while_paused.py` | 暂停状态下读内存（验证派生字段是否被重算） |
| `test_set_date_while_paused.py` | **暂停时设日期**，验证界面是否立即刷新 |
| `verify_date_after_resume.py` | 恢复流逝后复查日期是否被游戏覆盖 |

### 日期编码 / 字段定位（一次性用途，留作参考）

| 文件 | 作用 |
|---|---|
| `crosscheck_date_fields.py` | 交叉验证 raw 与派生字段 |
| `locate_hour_field.py` | 找「小时」字段 |
| `locate_hour_field_after_tick.py` | 同上，让游戏 tick 后再看 |
| `locate_hour_field_full_dump.py` | 同上，dump 更大范围 |
| `check_second_raw_copy.py` | 检查是否存在第二份 raw 副本 |
| `check_second_raw_copy_after_enter.py` | 同上，进图后再查 |
| `scan_heap_for_year_value.py` | 全堆扫「年份值」 |
| `scan_game_state_window.py` | 扫 CGameState 前 0x8000 |
| `read_address_around.py` | 读某个绝对地址附近 |
| `sample_address_twice.py` | 隔 8 秒采样同一地址两次，看哪些字段在变 |
| `compare_two_dates_run.py` | 上面 `compare_two_dates.js` 的驱动 |
| `find_date_structures_run.py` | 上面 `find_date_structures.js` 的驱动 |
| `find_date_structures_narrow_run.py` | 上面窄化版的驱动 |
| `set_game_date_fixed_510.py` | 固定设成 510.6.7（早期验证用） |
| `single_session_full_test.py` | **单会话完整测试**（暂停设日期 → 看派生字段 → 恢复流逝） |

## 典型用法

**验证「暂停时也能立刻改日期」**：

```
python -u modules/gamedate/read_game_date_fields.py          # 记下当前
python -u modules/gamedate/test_set_date_while_paused.py     # 暂停下写入并检查
python -u modules/gamedate/read_game_date_fields.py          # 复查
```

**验证加减法**：

```
python -u modules/gamedate/test_add_time_commands.py         # 指令（8 个用例）
python -u modules/gamedate/test_add_time_effects.py          # effect（8 个用例）
```

## 注意

- `read_game_date_fields.py` 里的 `+0x4C0` 是**防重入状态位，绝不能写**（写过一次，游戏当场退出）
- 派生字段（`+0x478` 等）由游戏每帧重算，**界面不读它们**，界面读的是 raw
- 加减 effect 需要 mod 里有 `events/zz_datetest.txt`（11 个事件）
