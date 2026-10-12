import hashlib, json, pathlib, shutil, subprocess, sys, zipfile
ROOT=pathlib.Path(__file__).resolve().parents[3];TX=ROOT/'test/reports/20261012_variable64_transaction';A=TX/'array_group'
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf-8'))
native=read(A/'native_v2/comparison.json');unit=read(A/'unit_final/result.json')
assert native['exit']==0 and native['checks']==native['passed'] and native['alive']
assert unit['exit']==0 and 'checks=2084 passed=2084 failed=0' in unit['stdout']
assert native['expanded_sha256']==unit['expanded_sha256']
assert sha(ROOT/'src/plugin/SDK_RVA/variable64/variable64.c')=='ec54864342e9e8811aaea73eb7ef66ed5f4f9328a7083854120f190880755c1e'
assert sha(ROOT/'src/plugin/SDK_RVA/trigger/trigger_reg.c')=='40a65b4311177fd90849bae69dea429f8e94ec71e2a95acec6b68fb22c7621a3'
old=read(TX/'VERIFICATION.txt')
if not (A/'pre_group_VERIFICATION.txt').exists():shutil.copyfile(TX/'VERIFICATION.txt',A/'pre_group_VERIFICATION.txt')
with zipfile.ZipFile(TX/'MODIFIED_FILE.zip') as z:paths=set(z.namelist())
paths.update(['src/plugin/SDK_RVA/variable64/array64_group_readonly.c','src/plugin/SDK_RVA/variable64/native_array_readonly.c',
 'ai_docs/09_脚本数值系统/Array64保留组解码与存档边界.md','ai_docs/09_脚本数值系统/Array64显式协议设计.md','ai_docs/09_脚本数值系统/当前状态与复现.md',
 'test/modules/effect/test_array64_group_native.py','test/modules/effect/verify_array64_group.py',
 'test/modules/effect/audit_array_group_package.py','test/modules/effect/finalize_array_group_transaction.py'])
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
 p=subprocess.run([sys.executable,str(ROOT/'test/modules/effect/audit_array_group_package.py'),str(path)],capture_output=True);assert p.returncode==0,p.stderr
 audit[label]={'command':[sys.executable,str(ROOT/'test/modules/effect/audit_array_group_package.py'),str(path)],'stdout':p.stdout.decode('utf-8'),'stderr':p.stderr.decode('utf-8'),'exit':p.returncode};print(label,audit[label]['stdout'].strip())
assert json.loads(audit['baseline']['stdout'])['group_decoder_present']==json.loads(audit['rollback']['stdout'])['group_decoder_present']==False
assert json.loads(audit['modified']['stdout'])['group_decoder_present']==True
with zipfile.ZipFile(TX/'MODIFIED_FILE.zip') as z:
 assert z.testzip() is None
 for n in z.namelist():assert z.read(n)==(ROOT/n).read_bytes()
old['array_group_decoder_extension']={'symbol':'Array64Group_Read','protocol_version':2,'indexed64_enabled':False,'original_scalar_sources_unchanged':True,
 'real_native_lifecycle':native,'synthetic_native_fixture':unit,'package_three_state':audit,
 'package_rollback_exact':True,'patch_reconstructs_exact_package':True,
 'real_commands':{p:read(A/('native_v2/'+p+'_commands.json')) for p in ['write','reload']},
 'native_save_sha256':sha(A/'native_v2/save_snapshot.hoi4'),
 'retained_failures':[read(A/'native_v1/FAILED_v1_comparison.json')],
 'errors_retained':['Document patch helper default GBK decoding raised UnicodeDecodeError (child Python exit1); rerun with explicit UTF-8 succeeded.', 'Original capture count assertion rejected native duplicate callbacks; corrected by checking every callback against first resolved scope samples. Original process exit1 retained in native_v1_console.txt.', 'Protocol v1 signed32-min component serialized as --2147483648; full raw min became0 on reload. Version2 escaped components and rejected v1.'],
 'remaining':['native staged write/compensation and quarantine','production plugin integration','hot reload and all save formats','multiplayer/threading']}
old['latest_modified_hashes']={p:hashlib.sha256(b).hexdigest() for p,b in new.items()}
(TX/'VERIFICATION.txt').write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8')
roles={}
for n in ['MODIFIED_FILE.zip','DIFF_FILE.patch','VERIFICATION.txt','ROLLBACK.sh']:
 p=TX/n;b=p.read_bytes();roles[n]={'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)};print(json.dumps(roles[n],ensure_ascii=False))
(TX/'artifact_hashes.json').write_text(json.dumps(roles,ensure_ascii=False,indent=2),encoding='utf-8')
(TX/'checkpoint.json').write_text(json.dumps({'ACTIVE_OBJECT':str(ROOT/'src/plugin/SDK_RVA/variable64/variable64.c'),
 'LAST_CONFIRMED_RESULT':'Array64Group_Read readonly native reserved groups validated in five scopes and saved/restarted. v1 signed32-min serialization defect reproduced and preserved; version2 escape codec restores full signed raw64 and rejects malformed groups. Synthetic native2084/2084. Writes remain disabled.',
 'NEXT_EXECUTABLE_ACTION':'Verify native staged-write and compensation primitives on isolated fixture copies, including odd-generation quarantine and fault recovery, before registering any public Array64 write API',
 'INPUT_PATHS':[str(ROOT/'ai_docs/09_脚本数值系统/Array64保留组解码与存档边界.md'),str(A/'native_v2/comparison.json')],
 'ACCEPTANCE_EVENT':'Real native controlled writes and injected failures restore the exact group or leave odd-generation quarantine, without touching same-name native objects'},ensure_ascii=False,indent=2),encoding='utf-8')
print('ARRAY_GROUP_TRANSACTION_VERIFIED')
