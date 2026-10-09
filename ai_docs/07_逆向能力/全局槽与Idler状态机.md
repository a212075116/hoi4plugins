# 全局槽与 Idler 状态机

> 依据：Frida 运行时实证（主菜单 vs 游戏内两次对比）
> 探针：test/probes_js/_probe_obj.js

## 0x332F698 不是「摄像机指针」，是「当前 Idler」

早期把它当成固定的摄像机宿主，导致在错误时机读到垃圾值。
**实际它是一个随游戏状态变化的状态机指针。**

## 两次实证对比

| 项 | 主菜单 | 游戏内 |
|---|---|---|
| 类名（RTTI） | **CFrontEndIdler** | **CInGameIdler** |
| obj->vftable | rva 0x2949d50 | rva 0x2968ff0 |
| obj+0x750 | **0x0** | **有效 cam 指针** |
| vt[0x130] | rva 0xb3bab0（不是 getter） | **rva 0xdc53b0 = sub_140DC53B0** |

**同一个偏移，在两个状态下含义完全不同。**

## 交叉印证：源码文件名

游戏自己的日志里出现了类名对应的源文件：

    [16:32:25][1936.01.01.12][ingameidler.cpp:5173]: Start RestoreDeviceObjects
    [16:32:26][1936.01.01.12][ingameidler.cpp:5323]: End RestoreDeviceObjects

日志路径：%USERPROFILE%/Documents/Paradox Interactive/Hearts of Iron IV/logs/game.log

**RTTI 说是 CInGameIdler，日志说是 ingameidler.cpp —— 两条独立证据一致。**

## 正确的取摄像机方式

先确认当前是 CInGameIdler：

    cam = *(void**)(obj + 0x750);

或更稳健地走虚调用（不依赖偏移）：

    cam = ((void*(*)(void*))vt[0x130/8])(obj);

**两条路结果一致（已实证）。**

## 已知全局槽

| RVA | 内容 | 引用数 |
|---|---|---|
| 0x332F260 | CGameState* | 12687 |
| 0x332F698 | 当前 Idler（CFrontEnd / CInGame） | 2356 |

## 教训

**全局槽的语义会随游戏状态变化。**
任何「某个全局槽就是某个对象」的假设，都必须在目标状态下重新验证一次。

这也是为什么本项目早期在 Frida spawn 的进程里读到 obj+0x750 = 0x4100000100
（垃圾值）—— 那时游戏还在主菜单，指针指的是 CFrontEndIdler。