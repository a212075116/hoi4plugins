# 拦截 -debug 自动打开日志

> 目标：带 `-debug` 启动时，游戏不再自动弹出记事本显示 `logs/error.log`。

## 结论

**已实现**：插件对游戏的 IAT 打补丁，拦掉「用 notepad 打开 .log」的进程创建调用。
本功能可单独开关（`ProcBlock_SetEnabled`），与崩溃文件重定向互不影响。

实测日志（`reports/mod_loader_tbb.log`）：

    [pblock] installed A=00007FF6C87D7490 W=00007FF6C87D77C0
    [plugin] ProcBlock_Install -> 1
    [pblock] blocked #1 A: "notepad" "C:\Users\...\logs/error.log"
    [pblock] blocked #2 A: "notepad" "C:\Users\...\logs/error.log"

同时确认：没有 notepad 进程、游戏正常进地图、其它插件功能（effect 注册 4/4、
console 命令 5 个、类结构校验 2/2）全部照常。

## 游戏是怎么打开日志的

用 Frida hook `CreateProcessA/W` 抓到实际调用：

    CreateProcessA lpCommandLine = "notepad" "C:\Users\<用户>\Documents\Paradox
                                 Interactive\Hearts of Iron IV/logs/error.log"

调用栈（RVA）：`0x175bb4` ← `0x1810f1` ← `0x12878c` ← `0x25897d2` ← `0x251a44e`

直接调用点是 `hoi4.exe+0x175bae`，是一条 `call qword ptr [rip+...]` 的 IAT 间接调用：

    175ba5:  mov rdi, [rbp - 0x70]          ; 命令行
    175bac:  xor ecx, ecx
    175bae:  call qword ptr [rip + 0x25918dc]   ; -> CreateProcessA
    175bb4:  test eax, eax                       ; 失败分支 0x175bd3

## 试过但无效的做法

| 做法 | 结果 |
|---|---|
| 改全局 `hoi4.exe+0x332ECF0`（`0x175b20` 处 `cmp [全局], eax; jg skip`） | **无效**，改成 `INT_MAX` 后记事本照样弹出。该分支不决定是否打开日志 |
| 找配置项（`settings.txt` / `pdx_settings.txt`） | 没有控制此行为的项 |
| 网上现成方案 | 只找到同问题的求助帖（r/hoi4modding），无解法 |

`0x175b20` 那条判断的真实语义**未查明**。

## 实现要点

### 1. 只改 IAT 槽，不做 inline hook

与崩溃重定向同一套做法（见《崩溃文件重定向.md》）：运行时解析 PE 导入表拿到槽地址，
`VirtualProtect` 改成可写后替换，不硬编码地址。

### 2. 拦截判定

命令行（或 `lpApplicationName`）同时满足两条才拦：

- 含 `notepad`（不分大小写）
- 含 `.log`（不分大小写）

这样不绑定具体日志路径，`-debug` 打开别的日志也会一并拦掉，
同时不会误伤游戏正常创建的子进程（实测 `passed=0`，无漏网）。

### 3. 拦下后返回 FALSE 而不是伪造成功

```c
ClearProcessInfo(pi);
SetLastError(ERROR_ACCESS_DENIED);
return FALSE;
```

游戏在 `0x175bb4` 有失败分支（`test eax,eax / je 0x175bd3`），能正常容错。
实测游戏不崩、正常进地图。

## 踩坑：部署必须拷两个产物

第一次部署只覆盖了 `tbb.dll`（载体），忘了拷 `hoi4_mod_plugin.dll`（插件），
结果新代码根本没被加载、拦截无效。

**载体只做导出转发，业务全在插件里。改插件后必须重新部署插件产物。**
（见《构建方式.md》的部署一节。）

## 源码

| 文件 | 作用 |
|---|---|
| `src/plugin/SDK_RVA/hook/process_block.h` | 接口：安装 / 已安装 / 拦截计数 / 开关 |
| `src/plugin/SDK_RVA/hook/process_block.c` | 实现 |
| `src/plugin/plugin_main.c` | 在 `FileRedirect_Install()` 之后调用 `ProcBlock_Install()` |

## 备份

部署前原版 `tbb.dll` 备份为 `tbb.dll.bak_before_pblock`（游戏根目录）。
