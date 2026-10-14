# 虚表与 RTTI

> 依据：IDA 9.0 静态分析 + Frida 运行时实证
> 探针：test/probes_ida/_vt_probe*.py、test/probes_js/_probe_obj.js

## 一、能否直接访问虚函数表

**能，而且已经验证过。**

对于已验证的多态子对象，其 vptr 位于该子对象开头；不要推广为所有对象都只有一个首部虚表：

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

### 关键区别：COL 内部是 4 字节 RVA，表前缀是 8 字节指针

旧文档此处错误地称标准 MSVC x64 RTTI 内部使用 8 字节绝对地址。2026-10-14 更正：
正常含 RTTI 的 Microsoft x64 COL 内部类型/类层级/自引用字段使用 32 位 image-relative 值，这是常规 ABI，不是 HOI4 特例。
vftable[-1] 指向 COL 的前缀指针仍是 64 位，不能混淆两者。
依据：[LLVM Microsoft ABI 实现](https://github.com/llvm/llvm-project/blob/main/clang/lib/CodeGen/MicrosoftCXXABI.cpp#L454-L547)。

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
| +0x14 | **0x02cdec08** | pSelf（RVA） |

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

这些是候选判据，不应无界向前扫；还需检查映像/节范围、pSelf、函数目标与主/次级子对象差异。
多继承可能使一个类名对应多个表，不能取第一个当成唯一结果。

从 0x142969118（CInGameIdler 的一个槽）往前扫 37 个槽，
得到虚表起点 0x142968ff0 —— 与静态分析的 RVA 0x2968ff0 一致。

2026-10-14 两映像复核见[接口复核](有没有官方接口.md)。类名定位不证明槽位语义跨版本保持。
