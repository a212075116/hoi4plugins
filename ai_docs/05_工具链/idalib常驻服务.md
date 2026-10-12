# idalib 常驻服务

> 脚本：test/lib/idalib_server.py、test/lib/idalib_cli.py
> （早期路径为 `flirt/idalib_server.py`，目录 flirt/ 已不存在，见文末）
> 数据库：hoi4plugins/sources/1.19.3/hoi4.exe.i64

## 为什么需要它

idat.exe 每次批处理要重新加载 865 MB 的 .i64 并 auto_wait，**实测 3-5 分钟**。
idalib 是进程内库，加载一次后所有查询都是**毫秒级**。

| 方式 | 开库耗时 |
|---|---|
| idat.exe 批处理 | 3-5 分钟 |
| idalib 常驻服务 | **5.7 秒** |

## 环境

    os.environ['IDADIR'] = r'D:\IDA Professional 9.0'
    idapro.open_database(I64, False)

历史实测使用本机IDA9.0。旧记录中的9.4许可证状态不是当前安装清单；本轮不重新核验许可证，实际运行前确认IDADIR与可用工具。
idalib 与 idat.exe **互斥**（都会锁 .i64），不能同时开。

## 协议

TCP 127.0.0.1:19531，一行一个 JSON 请求 -> 一行一个 JSON 响应。

| op | 参数 | 说明 |
|---|---|---|
| ping | | 探活 |
| decompile | ea, lines | 反编译（Hex-Rays） |
| disasm | ea, count | 反汇编 |
| xrefs_to | ea | 交叉引用 |
| func | ea | 函数信息（start/end/size/name） |
| strings | needle, limit | 搜字符串 |
| names | needle, limit | 搜符号名 |
| vtable | ea, max | 读虚表 |
| bytes | ea, n | 读原始字节 |
| read_str | ea, n | 读字符串 |
| grep_disasm | pattern, limit | 在反汇编文本里搜子串（**注意是子串不是正则**） |
| shutdown | | 关闭 |

## 一个必须记住的限制

**IDA API 只能在主线程调用。** 早期给每个连接开 threading 会报：

    RuntimeError: Function can be called from the main thread only

所以服务是**串行**处理请求的。

## 用法

    python hoi4plugins/test/lib/idalib_server.py          # 后台常驻
    python hoi4plugins/test/lib/idalib_cli.py decompile 0x140DC53B0

改 .i64 路径的位置在 idalib_server.py 第 26 行的 I64 常量。

## 本项目用它查到的东西

- 命令表项结构（sub_1400036F0 的构造序列）
- 管理器布局（sub_1424B4920 / sub_1424B5CC0）
- handler 签名（sub_140241DF0）
- 摄像机 getter（sub_140DC53B0）
- CString::assign（sub_140129CA0）

## 路径变更记录

早期所有探针脚本都放在 `flirt/` 下（`flirt/loader/`、`flirt/`、`flirt/idalib_*.py`），
后来重组为：

| 旧路径 | 现路径 |
|---|---|
| `flirt/idalib_server.py` | `test/lib/idalib_server.py` |
| `flirt/idalib_cli.py` | `test/lib/idalib_cli.py` |
| `flirt/loader/frida_host.py` | `test/lib/frida_host.py` |
| `flirt/loader/*.js` | `test/probes_js/*.js` |
| `flirt/脚本.py`（ida 批处理） | `test/probes_ida/*.py` |

**`flirt/` 目录现已不存在。** 若在某处看到 `flirt/...` 字样：

- `ai_docs/` 里若出现，说明那处还没更新，请按上表改正；
- `test/probes_py/*.py`、`test/probes_frida/frida_*.py` 等**历史脚本**里仍留有旧路径，
  它们大多已失效，**不要照抄**，新脚本参照test/lib公共库与test/modules现有驱动；历史probes目录不是现行入口。
