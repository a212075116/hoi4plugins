# flirt/ 脚本索引

在 `hoi4.exe.i64` 上做 FLIRT 签名恢复与 C++ RTTI 结构恢复的全部脚本。
所有脚本都通过 `FLIRT_JOB` 环境变量接收 JSON 配置，**路径不硬编码**。

## 运行方式

```powershell
Set-Location 'D:/SteamLibrary/steamapps/common/Hearts of Iron IV'
$env:FLIRT_JOB = "$PWD/flirt/job_xxx.json".Replace('\','/')
& 'D:/IDA Professional 9.0/idat.exe' -A -S"$PWD/flirt/脚本.py" -L"$PWD/reports/ida_xxx.log" "work/db/hoi4.exe.i64"
```

> 长任务（数千次改名）**必须后台跑**：单次命令有 120 秒上限，超时会被中断（中断时数据库不写入，安全）。
> 改库前先备份到 `work/db.bak/`，回退只需把文件拷回 `work/db/`。

## 一、FLIRT 签名

| 脚本 | 作用 |
| --- | --- |
| `ida_flirt_apply.py` | 按 `signatures` 列表批量应用 `.sig`（`plan_to_apply_idasgn` + `auto_wait`）|
| `ida_flirt_verify.py` | 只读复核已应用签名与命名数 |
| `ida_name_sample.py` | 抽样查看命名结果 |

## 二、RTTI / 虚表诊断（全部只读）

| 脚本 | 作用 |
| --- | --- |
| `ida_rtti_diag.py` | 统计名字表桶分布（`??_7` / `??_R` / mangled / 其它）|
| `ida_vftable_diag.py` | 虚表槽位命名率诊断 |
| `ida_vftable_verify.py` | 命名后状态验证 |
| `ida_vfunc_quality.py` | 名字可读性评估（clean / ugly）|
| `ida_demangle_probe.py` | `??_7` 符号 demangle 格式探查 |
| `ida_vt_unparsed_probe.py` | 未解析符号排查 |
| `ida_plugin_probe.py` | 探查已安装 IDA 插件 |

## 三、RTTI 结构布局反推（只读）

| 脚本 | 作用 |
| --- | --- |
| `ida_rtti_layout_probe.py` | 按假设布局试读 `??_R3` 字段 |
| `ida_rtti_raw_dump.py` | **dump 原始字节反推真实布局**（发现 x64 指针是 4 字节 RVA）|
| `ida_vt_diag2.py` | 查看单个类的全部 `??_7` 符号与槽位内容 |
| `ida_vt_diag3.py` | 检查 IDA 对虚表的原生标注（item size / next symbol）|
| `ida_vt_boundary.py` | 用 COL 边界判据求虚表真实槽位数 |
| `ida_vt_impact.py` | 量化越界读取规模（结论：越界为 0）|

## 四、类结构恢复与命名

| 脚本 | 作用 |
| --- | --- |
| `ida_rtti_hierarchy.py` | **从 `??_R2`/`??_R3` 还原类继承层次**，输出 JSON |
| `ida_vftable_name.py` | 虚函数命名 v1（先到先得，按符号表顺序）|
| `ida_vftable_name2.py` | **虚函数命名 v2（按继承深度自顶向下）**，支持 dry-run |
| `ida_vfunc_audit.py` | 用继承层次审计命名归属 |
| `ida_vfunc_sim.py` | 只读模拟两种命名顺序的归属准确率 |
| `ida_vfunc_verify2.py` | v2 命名后的归属准确率 + 质量验证 |
| `make_hierarchy_report.py` | 把继承 JSON 渲染成 Markdown（本机 Python，不需 IDA）|

## 关键实测结论

1. **x64 MSVC RTTI 里结构内指针是 4 字节 RVA**，不是 8 字节绝对地址；imagebase 为 `0x140000000`。
   - `RTTIClassHierarchyDescriptor`：`+0x00` signature、`+0x04` attributes、`+0x08` numBaseClasses、`+0x0C` pBaseClassArray(RVA)
   - `RTTIBaseClassArray`：4 字节 RVA 数组，`[0]` 是类自身，之后按继承顺序排列基类
   - `RTTIBaseClassDescriptor`：`+0x00` pTypeDescriptor(RVA)，TypeDescriptor 的类名字符串在 `+0x10`
2. **vftable 边界判据**：每个 vftable 的 `-0x8` 处是指向自身 COL 的指针；内存布局为 `[表N槽位…][表N+1的COL][表N+1槽位…]`，所以「连续读到第一个非代码指针」与 COL 边界判据**结果完全一致**（实测越界 0）。
3. **命名顺序决定归属**：字母序下继承槽位只有 **5.5%** 归属正确，继承深度序下达到 **72.8%**。
4. IDA 9 内置 `rtti.dll` 已做透 RTTI 解析，第三方 ClassInformer / HexRaysPyTools / virtuailor 均已过时或版本不兼容。
