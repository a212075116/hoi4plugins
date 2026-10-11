import difflib
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
TX = ROOT/'test/reports/20261012_variable64_transaction'
TX.mkdir(exist_ok=True)
if (TX/'VERIFICATION.txt').exists():
    raise SystemExit('已有已完成事务；不要重写基线。后续记录应扩展该事务。')
STATUS = 'ai_docs/09_脚本数值系统/当前状态与复现.md'
paths = [
    'ai_docs/README.md',
    'ai_docs/09_脚本数值系统/variable64实现与验证.md',
    'ai_docs/09_脚本数值系统/variable64的effect实现.md',
    'ai_docs/09_脚本数值系统/log64位桥接.md',
    'ai_docs/09_脚本数值系统/变量运算effect的64位版.md',
    'ai_docs/09_脚本数值系统/变量运算符64位接入.md',
    'ai_docs/09_脚本数值系统/变量溢出挂账机制.md',
    'ai_docs/还未经过实际检验的发现/变量运算_原版运算符识别与64位兼容设计.md',
    'test/reports/20261011_1530_插件_variable64颜色实现_逆向链路与logUI差异定位.txt',
]
old = {p:(ROOT/p).read_bytes() for p in paths}
new = dict(old)
def put(p,txt): new[p]=txt.encode('utf-8')
def text(p): return old[p].decode('utf-8-sig')
def banner(p,note):
    s=text(p); first,rest=s.split('\n',1)
    put(p,first+'\n\n> 状态校正（2026-10-12）：'+note+'\n> 当前结论统一见《当前状态与复现.md》；下文保留历史过程，不能作为当前待办清单。\n'+rest)
banner(paths[1],'早期“双分量、固定变量名、存档待测、原版 log 截断”描述属于对应历史轮次；后续三分量与 log 桥接已完成，存档成功记录也已补齐。最新后缀为 `_var64h` / `_var64f`。')
banner(paths[2],'存档未实测与原版 log 无法完整显示的旧结论已被后续报告取代。本次原有回归通过，但新增长辅助槽名用例暴露语言桥接错误，不能笼统宣称所有名字都支持。')
banner(paths[3],'三分量已支持真实小数，不能再描述为“小数恒为零”。UI 颜色已由用户在 2026-10-12 明确确认解决，本轮未重新目视验收颜色。')
p=paths[3];s=new[p].decode('utf-8')
start=s.index('## 七之二、仍存在的限制');end=s.index('## 八、相关文档',start)
s=s[:start]+'''## 七之二、当前边界与历史结论校正

- 小数恒为零是早期双分量实现的限制；三分量实现已有真实小数输出，本次四则运算也复现了 105.25、2762.5、276.25 等结果。
- 旧的“高位为零无法识别”描述不再准确：语言桥接会读取分数分量，不能仅凭高位判断。最新规则下的完整跨进程往返仍需独立验收。
- 本次 `repro_small=1.5` 经 `[?repro_small]` 输出为 `-1`；源码的语言桥接辅助槽名仍按 SSO 构造，超过 15 字符的名字需要修复并复测。
- UI 颜色已由用户确认解决。历史颜色失败报告仅保留失败时的观察，不再列为当前缺陷。
- 语言桥接不应“读取时顺手登记”变量；原版运算接管只认写入侧显式登记或既有挂账，防止污染游戏内部变量。

'''+s[end:];put(p,s)
banner(paths[4],'独立 `_64` effect 与原版同名 effect 是不同入口。原版 clamp 的 min/max 已接入并在本次 8 项回归通过；round/modulo 原版同名 hook 仍停用。自定义 clamp_variable64 仍采用 value 边界参数。')
banner(paths[5],'加减乘除及变量操作数本次复现通过；历史 `_hi` / `_f` 已改为 `_var64h` / `_var64f`。作用域前缀与 trigger 路径未在本次验收。')
banner(paths[6],'挂账已扩展到乘除；本次 DB 6 项与 MB 6 项均复现通过。完整真值参与运算，回到 32 位范围后解除挂账。下文是加减法首阶段记录。')
put(paths[7],'''# variable64：未验证与尚未解决的问题

> 状态校正（2026-10-12）。只列仍未完成或本次新发现的事项。
> 当前实现与证据索引见 `../09_脚本数值系统/当前状态与复现.md`。

## 当前待办

1. **语言桥接长辅助槽名**：`repro_small=1.5` 本次显示为 `-1`。`Var64_LangResolveSlotValue` 仍用 SSO 填所有名字，需按容量正确构造堆字符串再复测。
2. **原版 round_variable / modulo_variable 接入**：两个 hook 已回退并保持停用。独立的 round_variable64 / modulo_variable64 已有通过记录，不能混为一谈。
3. **最新格式跨进程存档验收**：旧双分量、旧后缀三分量有成功报告。本次 savegame 探针返回 `out->ok=0` 和 access violation，没有生成新存档，不能把随后旧存档启动当成成功往返。
4. **trigger / 条件判断**：尚未验证，Effect 算术测试不能证明条件判断支持 64 位。
5. **作用域前缀操作数**：ENG.xxx / PREV.xxx 尚未验证；裸名字成功不能推广。
6. **运算 tooltip 参数与 $LEFT$/$RIGHT$**：仍未完成专项验收。
7. **其他变量入口**：随机赋值、clear、temp 系列与比较等还没有统一兼容验收。
8. **名字长度**：源码底层常量 40 包含辅助槽名；后缀长 7，理论主名最多 33。但主名读取与登记另有 32/31 限制，不能写成“40 字符主名已完整支持”。
9. **存档迁移**：`_hi` / `_f` 改名后的旧存档迁移尚未验证。

## 已从待办移除

| 原条目 | 校正 |
|---|---|
| 原版 clamp 未接入 | 2026-10-11 19:36 完成；本次 CL 8 项一致 |
| 乘除挂账尚未打通 | 2026-10-11 19:27 完成；本次 MB 6 项一致 |
| 必须给自定义 clamp_variable64 补 min/max | 已有原版 clamp_variable 的 min/max 入口，不应把不同接口混写 |
| UI 颜色未解决 | 用户 2026-10-12 明确确认已解决 |

## 保留的研究边界

十进制 H/L9/F 分段不是当前实现，也没有仅为换表示法进行改造的验收需求。
参数读取器最后一个参数的确切语义仍未查明；此前小数丢失已用直接读取完整变量分量修复。
''')
p=paths[8];put(p,'后续状态校正（2026-10-12）：用户明确确认 UI 颜色问题已经解决。本文件是 2026-10-11 15:30 的历史失败现场，不再代表当前缺陷；保留以下原始观察，不改写历史日志。\n\n'+text(p))
put(STATUS,'''# variable64 当前状态与复现

> 核对日期：2026-10-12；源码基线 `fae561d`。本页区分本次实测、历史实测与用户确认。

## 本次结果

Release|x64 构建退出码 0，部署两 DLL 后通过现成事件入口复现。
CL 8、MB 6、DB 6、VN 4、AR 7、AR2 8、M64 9 个选定断言共 **48/48** 一致。
M64 事件其他原始输出也完整保留，不把 48 个断言称为所有边界的全量覆盖。
插件日志的 temp_army 与 min/max 误登记污染检查为 0。

| 能力 | 当前结论 | 证据 |
|---|---|---|
| 原版四则运算 + 小数操作数 | 本次通过 | baseline_game.log、comparison.json |
| 32/64 混算加减与乘除挂账 | 本次通过 | DB、MB 输出 |
| 原版 clamp_variable min/max | 本次通过 | CL a1..a8 |
| 独立 round/modulo/clamp 的 `_64` 入口 | 选定用例本次通过 | M64 输出 |
| 原版 round/modulo 同名 hook | 停用，不宣称完成 | 当前 hook 安装日志 |
| 三分量与真实小数 log | 短辅助槽名成功，长名有新缺陷 | AR/VN 与 REPRO WRITE |
| UI 颜色 | 用户明确确认已解决；本次未目视重测 | 2026-10-12 用户消息 |
| 存档 | 历史版本有成功往返；最新版本本次未验收成功 | 本次 savegame out->ok=0、无新存档 |

## 存储与限制

当前辅助槽名为 `<name>_var64h` 与 `<name>_var64f`，不是旧 `_hi` / `_f`。
整数低位、高位与独立小数构成三分量；效果参数仍受 int64 ×100000 定点范围约束。
旧“只能输出整数”和“每变量只有两个槽”不再是当前实现。
`VAR64_NAME_LIMIT=40` 是底层名字限制，不等于 40 字符主名端到端通过。
后缀 7 字符、登记表和读取函数还存在不同边界，主名长边界需要专项验收。

## 本次新增失败现场

输入：`repro_big=92233720368546.05`、`repro_small=1.5`、`repro_neg=-1.5`、`repro_zero=0`。
原文：`REPRO WRITE marker=12026 big=92233720368546.05 small=-1 neg=-1.5 zero=-0`。
`Var64_LangResolveSlotValue` 对所有名字设置 cap=15；辅助槽名超过 SSO 容量时布局错误。
此为下一步 variable64 修复对象，不能用短名字回归通过掩盖。

savegame 探针进程退出码为 0，但命令内部 `out->ok=0`，并返回 access violation。
不存在本次指定的新存档；未把 -continuelastsave 加载的旧存档算成成功。
测试宿主首轮另有 GBK 输出异常（退出码 1）；已修正输出编码并保留原始错误日志。

## 复现入口与证据链

运行：`python -u test/modules/effect/reproduce_variable64.py`。
注意此脚本会部署、重启游戏并新增独立测试事件；存档失败会中止，不能据进程退出码判断游戏命令成功。
比较：`python test/modules/effect/verify_variable64_reproduction.py --regression-only`。
不带此参数时还要求新增用例和存档往返通过，当前失败应如实保留。

- Evidence：`test/reports/20261012_variable64_reproduction/baseline_game.log`、`baseline_plugin.log` 与 `comparison.json`。
- Finding：原有选定回归一致；新增长辅助槽名桥接错误；本次存档命令未成功。
- Path：先纠正文档状态，再修复语言桥接字符串布局，复跑相同输入并保持原版回归通过。

## 当前未完成

原版 round/modulo、作用域前缀、trigger、最新跨进程存档、旧存档迁移及变量名长度专项验收。
不要把探索轮次的“下一步”或后缀改名之前的通过报告直接视为当前版本的全面验收。
''')
p=paths[0];put(p,text(p).replace('## 目录','## 当前进展入口\n\nvariable64 最新状态优先看 [当前状态与复现](09_脚本数值系统/当前状态与复现.md)。模块文章中的探索过程与历史待办不自动代表当前状态。\n\n## 目录',1))

def archive(path,items):
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        for name,b in sorted(items.items()):
            i=zipfile.ZipInfo(name,(2026,10,12,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(i,b)
archive(TX/'BASELINE.zip',old)
archive(TX/'MODIFIED_FILE.zip',new)
for folder,source in [('before','BASELINE.zip'),('after','MODIFIED_FILE.zip')]:
 (TX/folder).mkdir(exist_ok=True)
 shutil.copyfile(TX/source,TX/folder/'MODIFIED_FILE.zip')
patch=subprocess.run(['git','diff','--no-index','--binary','--','before/MODIFIED_FILE.zip','after/MODIFIED_FILE.zip'],cwd=TX,capture_output=True)
if patch.returncode!=1: raise RuntimeError(patch.stderr)
(TX/'DIFF_FILE.patch').write_bytes(patch.stdout)
(TX/'docs.diff').write_text(''.join(''.join(difflib.unified_diff(old.get(p,b'').decode('utf-8-sig').splitlines(True),b.decode('utf-8').splitlines(True),fromfile=p,tofile=p)) for p,b in new.items()),encoding='utf-8')
(TX/'ROLLBACK.sh').write_text('#!/bin/sh\nset -eu\n[ "$#" -eq 1 ] || { echo "usage: ROLLBACK.sh target-copy.zip" >&2; exit 2; }\ndir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\ncat "$dir/BASELINE.zip" > "$1"\n',encoding='utf-8',newline='\n')
(TX/'audit_docs.py').write_text('''import sys,zipfile,json
with zipfile.ZipFile(sys.argv[1]) as z:
 s=z.read("ai_docs/09_脚本数值系统/log64位桥接.md").decode("utf-8-sig")
 corrected="状态校正（2026-10-12）" in s and "小数恒为零是早期" in s
 print(json.dumps({"historical_status_corrected":corrected},ensure_ascii=False))
 raise SystemExit(0 if corrected else 1)
''',encoding='utf-8')
records=[]
def command(label,args,cwd=None):
 r=subprocess.run(args,cwd=cwd,capture_output=True)
 records.append({'label':label,'command':args,'stdout':r.stdout.decode('utf-8',errors='replace'),'stderr':r.stderr.decode('utf-8',errors='replace'),'exit':r.returncode})
 return r
command('BASELINE',[sys.executable,str(TX/'audit_docs.py'),str(TX/'BASELINE.zip')])
command('MODIFIED',[sys.executable,str(TX/'audit_docs.py'),str(TX/'MODIFIED_FILE.zip')])
shutil.copyfile(TX/'MODIFIED_FILE.zip',TX/'restored.zip')
command('ROLLBACK_EXEC',['C:/Program Files/Git/bin/bash.exe',str(TX/'ROLLBACK.sh'),str(TX/'restored.zip')])
command('ROLLBACK',[sys.executable,str(TX/'audit_docs.py'),str(TX/'restored.zip')])
assert (TX/'restored.zip').read_bytes()==(TX/'BASELINE.zip').read_bytes()
rebuild=TX/'reconstruct';rebuild.mkdir(exist_ok=True)
command('PATCH_FIXTURE_INIT',['git','init','--quiet'],cwd=rebuild)
shutil.copyfile(TX/'BASELINE.zip',rebuild/'MODIFIED_FILE.zip')
r=command('PATCH_RECONSTRUCT',['git','apply','-p2',str(TX/'DIFF_FILE.patch')],cwd=rebuild)
assert r.returncode==0 and (rebuild/'MODIFIED_FILE.zip').read_bytes()==(TX/'MODIFIED_FILE.zip').read_bytes()
for p,b in new.items():
 (ROOT/p).write_bytes(b)
 assert (ROOT/p).read_bytes()==b
hashes={p:hashlib.sha256(b).hexdigest() for p,b in old.items()}
verification={'changed':'documentation status, current limitations, UI colour acceptance provenance','original_hashes':hashes,'commands':records,'rollback_hash_matches':True,'patch_reconstructs_exact_modified_zip':True}
(TX/'VERIFICATION.txt').write_text(json.dumps(verification,ensure_ascii=False,indent=2),encoding='utf-8')
for name in ['MODIFIED_FILE.zip','DIFF_FILE.patch','VERIFICATION.txt','ROLLBACK.sh']:
 p=TX/name;b=p.read_bytes();print(str(p),len(b),hashlib.sha256(b).hexdigest())
with zipfile.ZipFile(TX/'MODIFIED_FILE.zip') as z:assert z.testzip() is None
print(json.dumps(records,ensure_ascii=False,indent=2))
