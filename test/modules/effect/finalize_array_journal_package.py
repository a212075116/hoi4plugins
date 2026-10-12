import hashlib, json, pathlib, shutil, subprocess, sys, zipfile
ROOT=pathlib.Path(__file__).resolve().parents[3];TX=ROOT/'test/reports/20261012_variable64_transaction';A=TX/'array_journal'
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf-8'))
native=read(A/'native_fixed/comparison.json');unit=read(A/'unit_final/result.json')
assert native['exit']==0 and native['checks']==native['passed'] and native['alive']
assert unit['exit']==0 and 'checks=244 passed=244 failed=0' in unit['stdout']
assert native['expanded_sha256']==unit['expanded_sha256']
assert sha(ROOT/'src/plugin/SDK_RVA/variable64/variable64.c')=='ec54864342e9e8811aaea73eb7ef66ed5f4f9328a7083854120f190880755c1e'
assert sha(ROOT/'src/plugin/SDK_RVA/trigger/trigger_reg.c')=='40a65b4311177fd90849bae69dea429f8e94ec71e2a95acec6b68fb22c7621a3'
old=read(TX/'VERIFICATION.txt')
if not (A/'pre_journal_VERIFICATION.txt').exists():shutil.copyfile(TX/'VERIFICATION.txt',A/'pre_journal_VERIFICATION.txt')
with zipfile.ZipFile(TX/'MODIFIED_FILE.zip') as z:paths=set(z.namelist())
paths.update(['src/plugin/SDK_RVA/variable64/array64_shape_journal.c','src/plugin/SDK_RVA/variable64/array64_shape_transaction.c','src/plugin/SDK_RVA/variable64/array64_ownership_gate.c','src/plugin/SDK_RVA/variable64/array64_durable_snapshot.c','src/plugin/SDK_RVA/variable64/array64_recovery.c','src/plugin/SDK_RVA/variable64/array64_existing_transaction.c','src/plugin/SDK_RVA/variable64/array64_group_readonly.c','src/plugin/SDK_RVA/variable64/native_array_readonly.c',
 'ai_docs/09_脚本数值系统/Array64变长意图日志与重启修复.md','ai_docs/09_脚本数值系统/Array64显式协议设计.md','ai_docs/09_脚本数值系统/当前状态与复现.md',
 'test/modules/effect/test_array64_journal_native.py','test/modules/effect/verify_array64_journal.py',
 'test/modules/effect/audit_array_journal_package.py','test/modules/effect/finalize_array_journal_package.py'])
paths.update(str(p.relative_to(ROOT)).replace('\\','/') for p in (A/'native_fixed/records').glob('*'))
paths.add(str((A/'native_fixed/records.json').relative_to(ROOT)).replace('\\','/'))
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
 p=subprocess.run([sys.executable,str(ROOT/'test/modules/effect/audit_array_journal_package.py'),str(path)],capture_output=True);assert p.returncode==0,p.stderr
 audit[label]={'command':[sys.executable,str(ROOT/'test/modules/effect/audit_array_journal_package.py'),str(path)],'stdout':p.stdout.decode('utf-8'),'stderr':p.stderr.decode('utf-8'),'exit':p.returncode};print(label,audit[label]['stdout'].strip())
assert json.loads(audit['baseline']['stdout'])['journal_present']==json.loads(audit['rollback']['stdout'])['journal_present']==False
assert json.loads(audit['modified']['stdout'])['journal_present']==True
with zipfile.ZipFile(TX/'MODIFIED_FILE.zip') as z:
 assert z.testzip() is None
 for n in z.namelist():assert z.read(n)==(ROOT/n).read_bytes()
old['array_journal_extension']={'symbol':'Array64_JournalRecover','protocol_version':2,'indexed64_enabled':False,'original_scalar_sources_unchanged':True,
 'real_native_lifecycle':native,'synthetic_native_fixture':unit,'package_three_state':audit,
 'package_rollback_exact':True,'patch_reconstructs_exact_package':True,
 'real_commands':{p:read(A/('native_fixed/'+p+'_commands.json')) for p in ['write','reload']},
 'native_save_sha256':sha(A/'native_fixed/save_snapshot.hoi4'),
 'records_manifest':read(A/'native_fixed/records.json'),
 'retained_failures':{'startup':read(A/'startup_error.json'),'probe':read(A/'native_final/FAILED_probe_comparison.json')},
 'corrections':['CModule unresolved __chkstk removed by caller-owned opaque scratch, no replacement probe injected','NativeCallback pointers invoked via NativeFunction for real partial/mismatched fixture mutations'],
 'outcomes':{'failed_creation_removed':5,'existing_baselines_restored':15,'mismatch_or_foreign_rejected':10},
 'limits':['Not OS crash/atomic sidecar+game persistence','Trusted fixture scope/identity controller','No public API yet'],
 'remaining':['production effect/trigger integration','scope/parameter/tooltip verification','final regression and docs']}
old['latest_modified_hashes']={p:hashlib.sha256(b).hexdigest() for p,b in new.items()}
(TX/'VERIFICATION.txt').write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8')
roles={}
for n in ['MODIFIED_FILE.zip','DIFF_FILE.patch','VERIFICATION.txt','ROLLBACK.sh']:
 p=TX/n;b=p.read_bytes();roles[n]={'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)};print(json.dumps(roles[n],ensure_ascii=False))
(TX/'artifact_hashes.json').write_text(json.dumps(roles,ensure_ascii=False,indent=2),encoding='utf-8')
(TX/'checkpoint.json').write_text(json.dumps({'ACTIVE_OBJECT':str(ROOT/'src/plugin/SDK_RVA/variable64/variable64.c'),
 'LAST_CONFIRMED_RESULT':'Durable operation intents persisted before receipt/shape mutation; five scopes/30 groups restarted with genuine missing slots/column lengths/ownership. Receipt-bound recovery removed5 failed creations, restored15 baselines, rejected10 mismatched/foreign cases; native291/291 including30 wire oracles, unit244/244. Public API disabled.',
 'NEXT_EXECUTABLE_ACTION':'Integrate the verified owned/journal array64 backend into production effect and trigger interfaces with scoped parameters and explicit error/tooltip behavior; build/deploy and run real script API examples while preserving legacy indexed64 rejection',
 'INPUT_PATHS':[str(ROOT/'ai_docs/09_脚本数值系统/Array64变长意图日志与重启修复.md'),str(A/'native_fixed/comparison.json')],
 'ACCEPTANCE_EVENT':'A production build registers documented array64 script APIs and real game scripts execute scoped operations/queries with journal safety and observable errors, without legacy scalar/native-array regressions'},ensure_ascii=False,indent=2),encoding='utf-8')
print('ARRAY_JOURNAL_PACKAGE_VERIFIED')
