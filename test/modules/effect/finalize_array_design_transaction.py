import hashlib,json,pathlib,subprocess,shutil,sys,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[3];TX=ROOT/'test/reports/20261012_variable64_transaction';A=TX/'array_design'
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
model=read(A/'model/result.json');assert model['checks']==model['passed']==150732 and model['exit']==0 and not model['game_integration']
native=read(A/'native/comparison.json');assert native['passed']==6 and native['exit']==0 and native['marker_ok'] and not native['integrated_array64']
assert sha(ROOT/'src/plugin/SDK_RVA/variable64/variable64.c')=='ec54864342e9e8811aaea73eb7ef66ed5f4f9328a7083854120f190880755c1e'
assert sha(ROOT/'src/plugin/SDK_RVA/trigger/trigger_reg.c')=='40a65b4311177fd90849bae69dea429f8e94ec71e2a95acec6b68fb22c7621a3'
old=read(TX/'VERIFICATION.txt')
if not (A/'pre_design_VERIFICATION.txt').exists():shutil.copyfile(TX/'VERIFICATION.txt',A/'pre_design_VERIFICATION.txt')
with zipfile.ZipFile(TX/'MODIFIED_FILE.zip') as z:paths=set(z.namelist())
paths.update(['ai_docs/09_脚本数值系统/Array64显式协议设计.md','test/modules/effect/verify_array_native_lifecycle.py',
 'test/modules/effect/audit_array_design_package.py','test/modules/effect/finalize_array_design_transaction.py',
 'test/reports/20261012_variable64_transaction/array_design/protocol_model.html','test/reports/20261012_variable64_transaction/array_design/verify_model.cjs'])
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
 p=subprocess.run([sys.executable,str(ROOT/'test/modules/effect/audit_array_design_package.py'),str(path)],capture_output=True);assert p.returncode==0,p.stderr
 audit[label]={'stdout':p.stdout.decode('utf-8'),'stderr':p.stderr.decode('utf-8'),'exit':p.returncode};print(label,audit[label]['stdout'].strip())
assert json.loads(audit['baseline']['stdout'])['model_present']==json.loads(audit['rollback']['stdout'])['model_present']==False
assert json.loads(audit['modified']['stdout'])['model_present']==True
with zipfile.ZipFile(TX/'MODIFIED_FILE.zip') as z:
 assert z.testzip() is None
 for n in z.namelist():assert z.read(n)==(ROOT/n).read_bytes()
old['array_protocol_design_extension']={'production_source_changed':False,'indexed64_enabled':False,'protocol_version':1,
 'prototype_branch':'codex/array64-protocol-model','prototype_commit':'36cfa805e3b0dad733bf6e16ffa3abb45be1f497',
 'model':model,'model_snapshot_sha256':sha(A/'model/PROTOTYPE_snapshot.json'),'model_actions_sha256':sha(A/'model/actions.jsonl'),
 'native_reference_lifecycle':native,'native_write_commands':read(A/'native/write_commands.json'),'native_reload_commands':read(A/'native/reload_commands.json'),
 'native_save_snapshot_sha256':sha(A/'native/save_snapshot.hoi4'),'package_three_state':audit,
 'package_rollback_exact':True,'patch_reconstructs_exact_package':True,
 'errors_retained':['Browser file: URL blocked by security policy; no HTTP/alternate-surface workaround attempted. No browser visual verification claimed.'],
 'remaining':['native read-only array backend ABI','native staged writes/rollback/quarantine','reserved group native serialization','full array64 game integration','visual browser/HOI4 UI','multiplayer/threading']}
old['latest_modified_hashes']={p:hashlib.sha256(b).hexdigest() for p,b in new.items()}
(TX/'VERIFICATION.txt').write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8')
roles={}
for n in ['MODIFIED_FILE.zip','DIFF_FILE.patch','VERIFICATION.txt','ROLLBACK.sh']:
 p=TX/n;b=p.read_bytes();roles[n]={'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)};print(json.dumps(roles[n],ensure_ascii=False))
(TX/'artifact_hashes.json').write_text(json.dumps(roles,ensure_ascii=False,indent=2),encoding='utf-8')
(TX/'checkpoint.json').write_text(json.dumps({'ACTIVE_OBJECT':str(ROOT/'src/plugin/SDK_RVA/variable64/variable64.c'),
 'LAST_CONFIRMED_RESULT':'Array64 explicit protocol v1 documented; isolated parallel lo/hi/kind and version/gen/len, model10359 actions/150732 assertions; native ordinary-array insert/remove/restart6/6 with scalar isolated. Production source hashes unchanged and indexed writes remain rejected. Prototype captured on codex/array64-protocol-model.',
 'NEXT_EXECUTABLE_ACTION':'Implement and verify a read-only native array backend and storage-shape probe before any array64 write API or transaction compensation',
 'INPUT_PATHS':[str(ROOT/'ai_docs/09_脚本数值系统/Array64显式协议设计.md'),str(A/'native/comparison.json')],
 'ACCEPTANCE_EVENT':'A readonly backend identifies the exact scoped native array, count and elements without mutation, matching native expressions and restart data'},ensure_ascii=False,indent=2),encoding='utf-8')
print('ARRAY_DESIGN_TRANSACTION_VERIFIED')
