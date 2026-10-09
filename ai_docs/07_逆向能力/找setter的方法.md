# 找 setter 的方法

> 依据：外部实践 + 本项目在 HOI4 上的完整实证
> 脚本：test/probes_ida/vtable/_find_writer_69c.py、test/probes_js/_exec_cmd.js

## 为什么要找 setter

改游戏状态有两条路：**直接写内存** 或 **调用游戏自己的函数**。

本项目实测到的差异（摄像机高度，超范围输入）：

| 做法 | 结果 |
|---|---|
| 直接写 `cam+0x69C = 9999` | 写入成功，**留下约 2.5 秒的非法值窗口**，之后游戏主循环才夹回 3000 |
| 调 `sub_1412643F0(cam, 9999)` | **当场夹紧到 3000** |

所以在「值可能越界」或「对象有内部状态需要同步」时，调 setter 更稳。

## 参考依据

方法来自一篇实际案例（2024）：
[Reverse Engineering a Videogame. Part 1](https://medium.com/@valeriy.krygin/reverse-engineering-a-videogame-part-1-know-your-tools-7906f9bd0e3e)
作者 Valeriy Krygin 逆向 *Sea Dogs: To Each His Own* 改游戏速度。

他的路径：

1. 用 CheatEngine 的 Find out what writes to this address (F6) 找写入点
2. 反编译看写入点上下文，发现写入前是一个**虚函数调用** `call qword ptr [rax+0xC0]`
3. 下断点跟进去，确认那是个 setter（两参数：从哪读、写到哪）

**注意：我们这次没有用动态的「谁写了它」，而是用了静态搜索 + 调用者分析**。
两条路都能到，静态那条在已有 IDA 数据库时更快。

## 本项目的做法（可复用）

### 第 1 步：静态搜字段偏移的引用

    python test/probes_ida/vtable/_find_writer_69c.py

用 `grep_disasm '+69Ch'` 扫全部函数（144103 个，约 67 秒），得到 27 个函数 / 47 处指令。

在命中里挑出**写入**（`movss dword ptr [reg+69Ch], xmm`），本例得 8 处。

### 第 2 步：用「同时碰到的邻居字段」判定归属

**关键**：`+0x69C` 只是偏移，任何对象的这个偏移都一样。
要判断某个函数操作的是不是目标对象，看它**是否同时碰到该对象的其它已知字段**。

本例摄像机的已知字段区：`+0x674 / +0x678 / +0x67C / +0x684 / +0x69C / +0x6D0 / +0x6D4`。
候选那三个函数都操作 `+0x688 / +0x698 / +0x6A0 / +0x6A4 / +0x6A8 / +0x6AC`，
全在摄像机对象范围内 ⇒ 归属成立。

### 第 3 步：看谁调用它（这一步给出了最多信息）

xrefs + 反编译调用者，本例找到 `sub_1417CCC80`：

    void __fastcall sub_1417CCC80(__int64 a1, int a2)     // a2 = 滚轮方向
    {
      v4 = (*(__int64 (__fastcall **)(_QWORD))(**(_QWORD **)(a1 + 5224) + 304LL))(*(_QWORD *)(a1 + 5224));
      if ( a2 >= 0 ) sub_1412642A0(v4);      // 滚轮上 -> 增大
      else           sub_141264150(v4);      // 滚轮下 -> 减小
      *(_BYTE *)(a1 + 5241) = 1;
    }

**这段一次性确认了三件事**：

1. `a1+0x1468` 取出的对象，其**虚表 +0x130** 就是 cam getter（与运行时实证一致）
2. `sub_141264150` / `2A0` / `3F0` 的**第一个参数就是 cam**
3. 这是**鼠标滚轮**处理 ⇒ 语义确认

### 第 4 步：从反编译推赋值语义

    v5 = *(_QWORD *)(a1 + 1688);                                   // 打包读 +0x698 与 +0x69C
    *(float *)(a1 + 1688) = *(float *)&v5 + 0.0;
    *(float *)(a1 + 1692) = (float)(a2 - *(float *)(a1 + 1692)) + *((float *)&v5 + 1);
    //                      (新值 - 旧值) + 旧值  ==  新值

净效果 `cam+0x69C = a2` ⇒ 它是 setter。

被 **37 处引用** ⇒ 是游戏各处设置该值的公共入口（不是某个局部辅助函数）。

### 第 5 步：运行期实证（不可省）

反编译推出来的东西必须实调一次。

    python test/probes_frida/_setter_run.py     # 直接调 setter
    python test/probes_frida/_cmp_run.py        # 对比 直接写 vs 调 setter
    python test/probes_frida/_range_run.py      # 超范围行为

结果见 `hoi4plugins/test/reports/20261009_173105_*.txt`。

## 本次找到的调用链

| 函数 | 语义 |
|---|---|
| `sub_140DC53B0(idler)` | 取 cam（虚表 `+0x130`） |
| `sub_141264150(cam)` | 高度减小（滚轮下） |
| `sub_1412642A0(cam)` | 高度增大（滚轮上） |
| **`sub_1412643F0(cam, h)`** | **设置高度为 h** |
| `sub_141261320(cam, ...)` | 内部插值（上面三个都调它） |

## 通用化：怎么把方法用到别的字段

1. 确定目标字段的偏移（本项目靠 CheatEngine 停用笔 + 对比试验）
2. `grep_disasm` 搜该偏移，挑出写入指令
3. 用「邻居字段是否也属于同一对象」筛归属
4. 反编译调用者，找语义证据（鼠标/键盘/UI 回调、常量名、日志字符串）
5. 反编译候选，读赋值表达式确认它是「赋值」还是「增量」
6. 运行期实调 + 对比直接写，量化差异

## 局限与风险

- 静态搜 `+69Ch` 会命中**所有**对象的该偏移，必须逐个判归属，不能只看命中数
- `grep_disasm` 全库扫一次约 67 秒（144103 个函数）
- 调 setter 是**执行游戏代码**：若该函数假设了某个前置状态（未初始化/线程约束），
  可能崩。所以务必先用 Frida 在可丢弃的进程里试
- setter 的 RVA 与游戏版本强绑定
