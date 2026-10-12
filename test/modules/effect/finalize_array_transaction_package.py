import hashlib, json, pathlib, shutil, subprocess, sys, zipfile
ROOT=pathlib.Path(__file__).resolve().parents[3];TX=ROOT/'test/reports/20261012_variable64_transaction';A=TX/'array_transaction'
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf-8'))
native=read(A/'native_final/comparison.json');unit=read(A/'unit_final/result.json')
assert native['exit']==0 and native['checks']==native['passed'] and native['alive']
assert unit['exit']==0 and 'checks=1579 passed=1579 failed=0' in unit['stdout']
assert native['expanded_sha256']==unit['expanded_sha256']
assert sha(ROOT/'src/plugin/SDK_RVA/variable64/variable64.c')=='ec54864342e9e8811aaea73eb7ef66ed5f4f9328a7083854120f190880755c1e'
assert sha(ROOT/'src/plugin/SDK_RVA/trigger/trigger_reg.c')=='40a65b4311177fd90849bae69dea429f8e94ec71e2a95acec6b68fb22c7621a3'
old=read(TX/'VERIFICATION.txt')
if not (A/'pre_transaction_VERIFICATION.txt').exists():shutil.copyfile(TX/'VERIFICATION.txt',A/'pre_transaction_VERIFICATION.txt')
with zipfile.ZipFile(TX/'MODIFIED_FILE.zip') as z:paths=set(z.namelist())
paths.update(['src/plugin/SDK_RVA/variable64/array64_existing_transaction.c','src/plugin/SDK_RVA/variable64/array64_group_readonly.c','src/plugin/SDK_RVA/variable64/native_array_readonly.c',
 'ai_docs/09_脚本数值系统/Array64固定长度事务与失败隔离.md','ai_docs/09_脚本数值系统/Array64显式协议设计.md','ai_docs/09_脚本数值系统/当前状态与复现.md',
 'test/modules/effect/test_array64_transaction_native.py','test/modules/effect/verify_array64_transaction.py',
 'test/modules/effect/audit_array_transaction_package.py','test/modules/effect/finalize_array_transaction_package.py'])
new={p:(ROOT/p).read_bytes() for p in sorted(paths)}
with zipfile.ZipFile(TX/'MODIFIED_FILE.zip','w',zipfile.ZIP_DEFLATED) as z:
 for n,b in sorted(new.items()):
  i=zipfile.ZipInfo(n,(2026,10,12,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;z.writestr(i,b)
shutil.copyfile(TX/'BASELINE.zip',TX/'before/MODIFIED_FILE.zip');shutil.copyfile(TX/'MODIFIED_FILE.zip',TX/'after/MODIFIED_FILE.zip')
p=subprocess.run(['git','diff','--no-index','--binary','--','before/MODIFIED_FILE.zip','after/MODIFIED_FILE.zip'],cwd=TX,capture_output=True);assert p.returncode==1
(TX/'DIFF_FILE.patch').write_bytes(p.stdout);shutil.copyfile(TX/'BASELINE.zip',TX/'reconstruct/MODIFIED_FILE.zip')
p=subprocess.run(['git','apply','-p2',str(TX/'DIFF_FILE.patch')],cwd=TX/'reconstruct',capture_output=True);assert p.returncode==0,p.stderr
assert sha(TX/'reconstruct/MODIFIED_FILE.zip')==sha(TX/'MODIFIED_FILE.zip')
shutil.copyfile(TX/'MODIFIED_FILE.zip',TX/'restored.zip')
p=subprocess.run(['C:/Program Files/Git/bin/bash.exe',str(TX/'ROLLBACK.sh'),str(TX/'restored.zip')],capture_output=True);assert p.returncode==0
assert sha(TX/'restored.zip')==sha(TX/'BASELINE.zip')
audit={}
for label,path in [('baseline',TX/'BASELINE.zip'),('modified',TX/'MODIFIED_FILE.zip'),('rollback',TX/'restored.zip')]:
 p=subprocess.run([sys.executable,str(ROOT/'test/modules/effect/audit_array_transaction_package.py'),str(path)],capture_output=True);assert p.returncode==0,p.stderr
 audit[label]={'command':[sys.executable,str(ROOT/'test/modules/effect/audit_array_transaction_package.py'),str(path)],'stdout':p.stdout.decode('utf-8'),'stderr':p.stderr.decode('utf-8'),'exit':p.returncode};print(label,audit[label]['stdout'].strip())
assert json.loads(audit['baseline']['stdout'])['transaction_present']==json.loads(audit['rollback']['stdout'])['transaction_present']==False
assert json.loads(audit['modified']['stdout'])['transaction_present']==True
with zipfile.ZipFile(TX/'MODIFIED_FILE.zip') as z:
 assert z.testzip() is None
 for n in z.namelist():assert z.read(n)==(ROOT/n).read_bytes()
old['array_existing_transaction_extension']={'symbol':'Array64_SetExisting','protocol_version':2,'indexed64_enabled':False,'original_scalar_sources_unchanged':True,
 'real_native_lifecycle':native,'synthetic_native_fixture':unit,'package_three_state':audit,
 'package_rollback_exact':True,'patch_reconstructs_exact_package':True,
 'real_commands':{p:read(A/('native_final/'+p+'_commands.json')) for p in ['write','reload']},
 'native_save_sha256':sha(A/'native_final/save_snapshot.hoi4'),
 'injection_scope':'Logical failures before five native writes and four compensation steps in real game. Native adapter before/after writes, persistent failure and foreign change separately tested in synthetic native fixture, not OS crash injection.',
 'remaining':['new group creation','resize/insert/delete/clear transaction snapshots','explicit quarantine recovery','runtime pressure and all save formats','production API integration','multiplayer/threading']}
old['latest_modified_hashes']={p:hashlib.sha256(b).hexdigest() for p,b in new.items()}
(TX/'VERIFICATION.txt').write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8')
roles={}
for n in ['MODIFIED_FILE.zip','DIFF_FILE.patch','VERIFICATION.txt','ROLLBACK.sh']:
 p=TX/n;b=p.read_bytes();roles[n]={'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)};print(json.dumps(roles[n],ensure_ascii=False))
(TX/'artifact_hashes.json').write_text(json.dumps(roles,ensure_ascii=False,indent=2),encoding='utf-8')
(TX/'checkpoint.json').write_text(json.dumps({'ACTIVE_OBJECT':str(ROOT/'src/plugin/SDK_RVA/variable64/variable64.c'),
 'LAST_CONFIRMED_RESULT':'Array64_SetExisting fixed-length existing-group one-element transactions validated in five native scopes with success, five rollback boundaries and four quarantine boundaries; unchanged native same-name scalar/arrays; new save/restart retains outcomes; native unit1579/1579. Public writes remain disabled.',
 'NEXT_EXECUTABLE_ACTION':'Implement and verify explicit quarantined-group inspection and recovery using a validated owned baseline snapshot, plus repeated native runtime pressure, before creation/resize or public API integration',
 'INPUT_PATHS':[str(ROOT/'ai_docs/09_脚本数值系统/Array64固定长度事务与失败隔离.md'),str(A/'native_final/comparison.json')],
 'ACCEPTANCE_EVENT':'Quarantined valid/partial group is explicitly recovered to a new even generation from an owned checked snapshot with stale-snapshot rejection and native pressure evidence'},ensure_ascii=False,indent=2),encoding='utf-8')
print('ARRAY_TRANSACTION_PACKAGE_VERIFIED')
