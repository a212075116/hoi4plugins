# 虚表与 RTTI

> 依据：IDA 9.0 静态分析 + Frida 运行时实证
> 探针：test/probes_ida/_vt_probe*.py、test/probes_js/_probe_obj.js

## 一、能否直接访问虚函数表

**能，而且已经验证过。**

游戏对象的前 8 字节就是虚表指针：

    void** vt = *(void***)obj;          // obj->vftable

按索引调用：

    typedef long long (__fastcall *Fn)(void* self);
    Fn f = (Fn)vt[0x130 / 8];
    long long ret = f(obj);

## 二、实证记录

Frida 在游戏内（已进地图）执行，结果如下：

    obj          = 0x20c54eb2450
    obj->vftable = 0x7ff6f6628ff0   (rva 0x2968ff0)
    vt[0x130]    = 0x7ff6f4a853b0   (rva 0xdc53b0)
    obj+0x750    = 0x20ca9b8faf0    <- 直接读字段
    虚调用返回值 = 0x20ca9b8faf0    <- 调用 vt[0x130](obj)
    一致? YES

拿到 cam 后读字段，与用户 CE 实测完全一致：

    cam+0x69C = 310               (目标高度)
    cam+0x6D0 = 50                (下限)
    cam+0x6D4 = 3000              (上限)
    cam+0x678 = 310.04345703125   (当前高度)

## 三、RTTI：反查对象的类名

虚表往前 8 字节是 COL（Complete Object Locator），由它可拿到类名。

### 关键陷阱：这个 exe 的 RTTI 指针是 4 字节 RVA

标准 MSVC x64 RTTI 用 8 字节绝对地址，**但 hoi4.exe 不是**。

COL 的实际字节（位于 0x142cdec08）：

    01000000 00000000 00000000 d0c02303 30eccd02 08eccd02 00000000 00000000

按 4 字节拆：

| 偏移 | 值 | 含义 |
|---|---|---|
| +0x00 | 0x00000001 | signature（必须 == 1） |
| +0x04 | 0x00000000 | offset |
| +0x08 | 0x00000000 | cdOffset |
| +0x0C | **0x0323c0d0** | pTypeDescriptor（RVA） |
| +0x10 | **0x02cdec30** | pClassDescriptor（RVA） |

**按 8 字节读会把两个 RVA 拼成 0x2cdec0802cdec30 这种垃圾值**，
表现为「类名读出来是乱码」或「指针明显非法」。

正确读法：

    uint32_t tdRva = *(uint32_t*)(col + 0x0C);
    char* name = (char*)(imageBase + tdRva + 0x10);

（+0x10 是 TypeDescriptor 里名字的偏移）

### 类名格式

    .?AVCInGameIdler@@      ->  类名 CInGameIdler
    .?AVCFrontEndIdler@@    ->  类名 CFrontEndIdler

## 四、虚表起点怎么判

    vftable - 8 处存着它自己的 COL，且 COL.signature == 1
    且 COL+0x0C 指向的 TypeDescriptor 名字以 .?AV 开头

用这个判据从任意槽位往前扫，即可定位虚表起点与类名。

从 0x142969118（CInGameIdler 的一个槽）往前扫 37 个槽，
得到虚表起点 0x142968ff0 —— 与静态分析的 RVA 0x2968ff0 一致。