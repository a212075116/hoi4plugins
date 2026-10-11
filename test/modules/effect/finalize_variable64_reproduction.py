import difflib
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import time
import zipfile

ROOT=pathlib.Path(__file__).resolve().parents[3]
TX=ROOT/'test/reports/20261012_variable64_transaction'
OUT=ROOT/'test/reports/20261012_variable64_reproduction/modified'
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
deadline=time.time()+400
while time.time()<deadline:
    log=(TX/'modified_runtime_console.txt').read_text(encoding='utf-8-sig',errors='replace')
    if 'FINISHED alive= True' in log:break
    if 'Traceback' in log:raise RuntimeError(log[-3000:])
    time.sleep(2)
else:raise TimeoutError('modified runtime reproduction did not finish')
r=subprocess.run([sys.executable,str(ROOT/'test/modules/effect/verify_variable64_reproduction.py'),'--dir',str(OUT)],capture_output=True)
print(r.stdout.decode('utf-8'));print('RUNTIME_VERIFY_EXIT',r.returncode)
assert r.returncode==0,r.stderr.decode('utf-8',errors='replace')
comparison=json.loads((OUT/'comparison.json').read_text(encoding='utf-8'))
assert comparison['reload']==['marker=12026 big=92233720368546.05 small=1.5 neg=-1.5 zero=0']

p=ROOT/'ai_docs/09_脚本数值系统/当前状态与复现.md'
s=p.read_text(encoding='utf-8')
s=s.replace('源码基线 `fae561d`','源码基线 `fae561d`，本次追加语言桥接字符串布局修复')
s=s.replace('| 三分量与真实小数 log | 短辅助槽名成功，长名有新缺陷 | AR/VN 与 REPRO WRITE |','| 三分量与真实小数 log | 长辅助槽名缺陷已修复，本次原版 log 输出正确 | 修改后 REPRO WRITE / READ |')
s=s.replace('| 存档 | 历史版本有成功往返；最新版本本次未验收成功 | 本次 savegame out->ok=0、无新存档 |','| 存档 | 最新后缀大数、小数、负数与零本次重启往返通过 | 新存档快照、READ 标记及比较结果 |')
s=s.replace('## 本次新增失败现场','## 新发现、修复与再验收')
s=s.replace('此为下一步 variable64 修复对象，不能用短名字回归通过掩盖。','已仅修改 `Var64_LangResolveSlotValue`：短名构造 SSO（含终止符），长名用外部字符串指针和真实容量。指针只借用于同步解析，不转移所有权。\n\n原生 C 夹具覆盖辅助槽名长度 8、16、18、17、39、40，修复后 6/6 通过。原版出现错误布局且 39 字符触发栈保护退出；回滚副本重现原版行为并恢复原始哈希。\n\n游戏修复后 WRITE 与重启读档后的 READ 原文均为：\n`marker=12026 big=92233720368546.05 small=1.5 neg=-1.5 zero=0`。\n原有 48 个选定断言再跑 48/48，污染为 0。')
s=s.replace('不存在本次指定的新存档；未把 -continuelastsave 加载的旧存档算成成功。','该失败尝试没有新存档，未把加载旧存档算成成功。随后改用短存档名 `v64repro12`，命令 `out->ok=1` / `Saved`，产生新文件；修改后重新写入用例、保存、退出、仅用 -continuelastsave 重启，再确认 marker=12026 和全部四个值。\n长存档名探针失败原因未在本轮进一步定位；这不是运行中 loadgame 已修复的证据。')
s=s.replace('存档失败会中止，不能据进程退出码判断游戏命令成功。','存档失败会中止（已补内层 out->ok 与新文件时间检查），不能据进程退出码判断游戏命令成功。')
s=s.replace('不带此参数时还要求新增用例和存档往返通过，当前失败应如实保留。','修改后证据目录需加 `--dir test/reports/20261012_variable64_reproduction/modified`；该目录不带 --regression-only 的检查本次退出码 0。原基线目录的新用例失败仍原样保留。')
s=s.replace('- Finding：原有选定回归一致；新增长辅助槽名桥接错误；本次存档命令未成功。','- Finding：原有选定回归一致；长辅助槽名桥接错误已修复；最新格式本次存档重启后完整恢复。')
s=s.replace('- Path：先纠正文档状态，再修复语言桥接字符串布局，复跑相同输入并保持原版回归通过。','- Path：已先纠正文档，再以基线—修改—回滚的原生夹具验证修复，并完成同输入游戏回归和存档重启验证。')
s=s.replace('原版 round/modulo、作用域前缀、trigger、最新跨进程存档、旧存档迁移及变量名长度专项验收。','原版 round/modulo、作用域前缀、trigger、读档后原版算术自动识别、挂账持久化、旧存档迁移及主变量名长度专项验收。\n本次存档往返仅验证所列四个值与本地作用域，不覆盖所有存档、作用域或挂账状态。')
p.write_text(s,encoding='utf-8')
p=ROOT/'ai_docs/还未经过实际检验的发现/变量运算_原版运算符识别与64位兼容设计.md'
s=p.read_text(encoding='utf-8')
s=s.replace('1. **语言桥接长辅助槽名**：`repro_small=1.5` 本次显示为 `-1`。`Var64_LangResolveSlotValue` 仍用 SSO 填所有名字，需按容量正确构造堆字符串再复测。','1. **读档后原版算术接管与挂账持久化**：本次重启后 log 完整恢复，不代表空登记表下原版算术及挂账状态已验收。')
s=s.replace('3. **最新格式跨进程存档验收**：旧双分量、旧后缀三分量有成功报告。本次 savegame 探针返回 `out->ok=0` 和 access violation，没有生成新存档，不能把随后旧存档启动当成成功往返。','3. **长存档名探针**：长名字 savegame 返回 access violation；短名 v64repro12 已成功完成最新格式的四个值和标记跨进程恢复。长名失败的具体原因未继续定位。')
s=s.replace('| UI 颜色未解决 | 用户 2026-10-12 明确确认已解决 |','| UI 颜色未解决 | 用户 2026-10-12 明确确认已解决 |\n| 语言桥接辅助槽长名布局错误 | 本轮修复，原生夹具 6/6、游戏新用例和重启读档通过 |\n| 最新格式没有读档证据 | 本轮新存档与四值恢复已验收；不扩大为所有算术路径通过 |')
p.write_text(s,encoding='utf-8')
p=ROOT/'ai_docs/09_脚本数值系统/log64位桥接.md'
s=p.read_text(encoding='utf-8').replace('- 本次 `repro_small=1.5` 经 `[?repro_small]` 输出为 `-1`；源码的语言桥接辅助槽名仍按 SSO 构造，超过 15 字符的名字需要修复并复测。','- 本次发现并修复超过 15 字符的辅助槽名 SSO 布局错误；`repro_small=1.5` 修改前为 `-1`，修改后原版 log 与重启读档均为 `1.5`。原生夹具覆盖到 40 字符辅助槽名，不等于 40 字符主名已通过。')
p.write_text(s,encoding='utf-8')

doc_stage=(TX/'VERIFICATION.txt').read_bytes()
(TX/'docs_stage_VERIFICATION.txt').write_bytes(doc_stage)
with zipfile.ZipFile(TX/'BASELINE.zip') as z:old={p:z.read(p) for p in z.namelist()}
with zipfile.ZipFile(TX/'MODIFIED_FILE.zip') as z:paths=z.namelist()
source='src/plugin/SDK_RVA/variable64/variable64.c'
old[source]=(TX/'variable64.BASELINE.c').read_bytes()
new={p:(ROOT/p).read_bytes() for p in paths}
new[source]=(ROOT/source).read_bytes()
assert new[source]==(TX/'variable64.MODIFIED.c').read_bytes()
def archive(path,items):
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
  for p,b in sorted(items.items()):
   info=zipfile.ZipInfo(p,(2026,10,12,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,b)
archive(TX/'BASELINE.zip',old);archive(TX/'MODIFIED_FILE.zip',new)
for folder,src in [('before','BASELINE.zip'),('after','MODIFIED_FILE.zip')]:shutil.copyfile(TX/src,TX/folder/'MODIFIED_FILE.zip')
r=subprocess.run(['git','diff','--no-index','--binary','--','before/MODIFIED_FILE.zip','after/MODIFIED_FILE.zip'],cwd=TX,capture_output=True)
assert r.returncode==1
(TX/'DIFF_FILE.patch').write_bytes(r.stdout)
(TX/'docs.diff').write_text(''.join(''.join(difflib.unified_diff(old.get(p,b'').decode('utf-8-sig').splitlines(True),b.decode('utf-8-sig').splitlines(True),fromfile=p,tofile=p)) for p,b in new.items()),encoding='utf-8')
records=[]
def cmd(label,args,cwd=None):
 r=subprocess.run(args,cwd=cwd,capture_output=True)
 records.append({'label':label,'command':args,'stdout':r.stdout.decode('utf-8',errors='replace'),'stderr':r.stderr.decode('utf-8',errors='replace'),'exit':r.returncode})
 return r
for label,file in [('BASELINE','BASELINE.zip'),('MODIFIED','MODIFIED_FILE.zip')]:cmd(label,[sys.executable,str(TX/'audit_docs.py'),str(TX/file)])
shutil.copyfile(TX/'MODIFIED_FILE.zip',TX/'restored.zip')
assert cmd('ROLLBACK_EXEC',['C:/Program Files/Git/bin/bash.exe',str(TX/'ROLLBACK.sh'),str(TX/'restored.zip')]).returncode==0
cmd('ROLLBACK',[sys.executable,str(TX/'audit_docs.py'),str(TX/'restored.zip')])
assert (TX/'restored.zip').read_bytes()==(TX/'BASELINE.zip').read_bytes()
shutil.copyfile(TX/'BASELINE.zip',TX/'reconstruct/MODIFIED_FILE.zip')
assert cmd('PATCH_RECONSTRUCT',['git','apply','-p2',str(TX/'DIFF_FILE.patch')],cwd=TX/'reconstruct').returncode==0
assert (TX/'reconstruct/MODIFIED_FILE.zip').read_bytes()==(TX/'MODIFIED_FILE.zip').read_bytes()
native=[]
for label in ['baseline','modified','rollback']:
 native.append({'label':label.upper(),'command':[sys.executable,str(ROOT/'test/modules/effect/test_var64_language_name.py'),str(TX/('variable64.'+{'baseline':'BASELINE','modified':'MODIFIED','rollback':'RESTORED'}[label]+'.c')),str(TX/('native_'+label))],
 'stdout':(TX/('native_'+label+'_stdout.txt')).read_text(encoding='utf-8-sig'),
 'stderr':(TX/('native_'+label+'_stderr.txt')).read_text(encoding='utf-8-sig'),
 'exit':int((TX/('native_'+label+'_exit.txt')).read_text(encoding='utf-8-sig').strip())})
assert (TX/'variable64.RESTORED.c').read_bytes()==old[source]
verification={'changed_symbol':'Var64_LangResolveSlotValue; SSO/external-pointer string field construction',
 'input_names':['x_var64f','repro_big_var64f','repro_small_var64f','repro_zero_var64f','abcdefghijklmnopqrstuvwxyz012345_var64f','abcdefghijklmnopqrstuvwxyz0123456_var64f'],
 'native_three_state':native,'docs_three_state':records,'runtime':comparison,
 'runtime_literal_command_log':str(TX/'modified_runtime_console.txt'),
 'original_hashes':{p:hashlib.sha256(b).hexdigest() for p,b in old.items()},
 'modified_hashes':{p:hashlib.sha256(b).hexdigest() for p,b in new.items()},
 'rollback_source_hash_matches':True,'rollback_package_hash_matches':True,'patch_reconstructs_exact_package':True,
 'errors_retained':['Initial harness UnicodeEncodeError/GBK: outer exit 1, event subprocess exit 0.',
 'Long savegame name: outer probe exit 0, inner out->ok=0/access violation; no fresh file. Short filename subsequently succeeds.',
 'First native harness compile invocation used a relative path with changed cwd: exit 1/FileNotFoundError; corrected to absolute paths.',
 'Initial source replacement failed CRLF matching: exit 1/AssertionError; corrected preserving original newlines.',
 'Initial binary patch reconstruction: header/path stripping errors and root-relative skipped patch; corrected same filename, -p2, isolated reconstruction repository.'],
 'build_warning':'Existing C4013 at variable64.c:1345: Var64_ReadParamValue declaration missing; not changed in this patch.',
 'scope':'Local source and installed local game 1.19.3; user-authorized reproduction, docs corrections and variable64 work.'}
(TX/'VERIFICATION.txt').write_text(json.dumps(verification,ensure_ascii=False,indent=2),encoding='utf-8')
for path in [ROOT/p for p in new]:assert path.read_bytes()==new[str(path.relative_to(ROOT)).replace('\\','/')]
with zipfile.ZipFile(TX/'MODIFIED_FILE.zip') as z:assert z.testzip() is None
roles={}
for n in ['MODIFIED_FILE.zip','DIFF_FILE.patch','VERIFICATION.txt','ROLLBACK.sh']:
 p=TX/n;b=p.read_bytes();roles[n]={'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
 print(json.dumps(roles[n],ensure_ascii=False))
(TX/'artifact_hashes.json').write_text(json.dumps(roles,ensure_ascii=False,indent=2),encoding='utf-8')
(TX/'checkpoint.json').write_text(json.dumps({'ACTIVE_OBJECT':str(ROOT/source),'LAST_CONFIRMED_RESULT':'48/48 regression; 6/6 native string-layout; fresh save/restart restores marker and four values; rollback hashes match','NEXT_EXECUTABLE_ACTION':'Verify post-load original arithmetic recognition before implementing round/modulo hooks','INPUT_PATHS':[str(OUT/'comparison.json'),str(ROOT/'ai_docs/09_脚本数值系统/当前状态与复现.md')],'ACCEPTANCE_EVENT':'post-load arithmetic uses full registered 64-bit value without intercepting vanilla variables'},ensure_ascii=False,indent=2),encoding='utf-8')
print('FINALIZED')
