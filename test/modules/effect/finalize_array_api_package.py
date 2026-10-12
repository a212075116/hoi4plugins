import hashlib, json, pathlib, shutil, subprocess, sys, zipfile
ROOT=pathlib.Path(__file__).resolve().parents[3];TX=ROOT/'test/reports/20261012_variable64_transaction';A=TX/'api'
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf-8'))
native=read(A/'native_final/comparison.json');unit=read(A/'legacy_registry/result.json')
assert native['exit']==0 and native['checks']==native['passed'] and native['alive']
assert native['deployed_dll_sha256']==sha(A/'hoi4_mod_plugin.MODIFIED.dll')
assert sha(ROOT/'src/plugin/SDK_RVA/variable64/variable64.c')=='ec54864342e9e8811aaea73eb7ef66ed5f4f9328a7083854120f190880755c1e'
assert read(A/'tooltips/comparison.json')['exit']==0
assert read(TX/'setter/api_legacy/comparison.json')['passed']==57
old=read(TX/'VERIFICATION.txt')
if not (A/'pre_api_VERIFICATION.txt').exists():shutil.copyfile(TX/'VERIFICATION.txt',A/'pre_api_VERIFICATION.txt')
with zipfile.ZipFile(TX/'MODIFIED_FILE.zip') as z:paths=set(z.namelist())
paths.update(['src/plugin/SDK_RVA/variable64/array64_api.c','src/plugin/plugin.vcxproj','src/plugin/plugin_main.c','src/plugin/SDK_RVA/effect/effect_reg.c','src/plugin/SDK_RVA/effect/effect_reg.h','src/plugin/SDK_RVA/trigger/trigger_reg.c','src/plugin/SDK_RVA/trigger/trigger_reg.h','src/plugin/SDK_RVA/variable64/array64_shape_journal.c','src/plugin/SDK_RVA/variable64/array64_shape_transaction.c','src/plugin/SDK_RVA/variable64/array64_ownership_gate.c','src/plugin/SDK_RVA/variable64/array64_durable_snapshot.c','src/plugin/SDK_RVA/variable64/array64_recovery.c','src/plugin/SDK_RVA/variable64/array64_existing_transaction.c','src/plugin/SDK_RVA/variable64/array64_group_readonly.c','src/plugin/SDK_RVA/variable64/native_array_readonly.c',
 'ai_docs/09_脚本数值系统/Array64脚本接口首轮接入.md','ai_docs/09_脚本数值系统/Array64显式协议设计.md','ai_docs/09_脚本数值系统/当前状态与复现.md',
 'test/modules/effect/verify_array64_api.py','test/modules/trigger/verify_array64_api_tooltips.py',
 'test/modules/effect/audit_array_api_package.py','test/modules/effect/finalize_array_api_package.py'])
paths.add('test/reports/20261012_variable64_transaction/api/hoi4_mod_plugin.MODIFIED.dll')
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
 p=subprocess.run([sys.executable,str(ROOT/'test/modules/effect/audit_array_api_package.py'),str(path)],capture_output=True);assert p.returncode==0,p.stderr
 audit[label]={'command':[sys.executable,str(ROOT/'test/modules/effect/audit_array_api_package.py'),str(path)],'stdout':p.stdout.decode('utf-8'),'stderr':p.stderr.decode('utf-8'),'exit':p.returncode};print(label,audit[label]['stdout'].strip())
assert json.loads(audit['baseline']['stdout'])['api_present']==json.loads(audit['rollback']['stdout'])['api_present']==False
assert json.loads(audit['modified']['stdout'])['api_present']==True
with zipfile.ZipFile(TX/'MODIFIED_FILE.zip') as z:
 assert z.testzip() is None
 for n in z.namelist():assert z.read(n)==(ROOT/n).read_bytes()
old['array_api_extension']={'symbol':'Array64_RegisterEffects/Array64_RegisterTriggers','protocol_version':2,'indexed64_enabled':False,'original_scalar_sources_unchanged':True,
 'real_native_lifecycle':native,'synthetic_native_fixture':unit,'package_three_state':audit,
 'package_rollback_exact':True,'patch_reconstructs_exact_package':True,
 'real_commands':{p:read(A/('native_final/'+p+'_commands.json')) for p in ['write','reload']},
 'native_save_sha256':sha(A/'native_final/save_snapshot.hoi4'),
 'build_stdout':(A/'build_final.stdout.txt').read_text(encoding='utf-8'),'build_stderr':(A/'build_final.stderr.txt').read_text(encoding='utf-8'),'build_exit':0,
 'baseline_dll_sha256':sha(A/'hoi4_mod_plugin.BASELINE.dll'),'modified_dll_sha256':sha(A/'hoi4_mod_plugin.MODIFIED.dll'),
 'tooltips':read(A/'tooltips/comparison.json'),
 'legacy_setter':read(TX/'setter/api_legacy/comparison.json'),'legacy_registry':unit,'legacy_tooltip':read(A/'legacy_tooltip/result.json'),'legacy_boundary':read(A/'legacy_boundary/result.json'),
 'retained_errors':{'first_api_console':(A/'native_v1_console.txt').read_text(encoding='utf-8'),'reason':'Native CSetVariable tooltip constructs uninitialized output, not append. Corrected and rebuilt; final event/save/reload inner ok1.'},
 'limits':['No visual hover/result-word encoding acceptance yet','Recovery API and abnormal-sidecar runtime matrix pending','No multiplayer or joint atomic persistence claim'],
 'remaining':['final script recovery/error/pressure lifecycle matrix','scope/tooltip visual and docs acceptance']}
old['latest_modified_hashes']={p:hashlib.sha256(b).hexdigest() for p,b in new.items()}
(TX/'VERIFICATION.txt').write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8')
roles={}
for n in ['MODIFIED_FILE.zip','DIFF_FILE.patch','VERIFICATION.txt','ROLLBACK.sh']:
 p=TX/n;b=p.read_bytes();roles[n]={'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)};print(json.dumps(roles[n],ensure_ascii=False))
(TX/'artifact_hashes.json').write_text(json.dumps(roles,ensure_ascii=False,indent=2),encoding='utf-8')
(TX/'checkpoint.json').write_text(json.dumps({'ACTIVE_OBJECT':str(ROOT/'src/plugin/SDK_RVA/variable64/variable64.c'),
 'LAST_CONFIRMED_RESULT':'array64_api.c compiled/deployed;10 effects and1 block trigger registered using native var/value parser; five scopes/scalar64 ROOT inputs, set64/native ownership, operations/errors and new save/restart69/69. Tooltip native calls4/4, legacy setter57/57, registry22/22, tooltip16/16, boundary8/8. Indexed scalar64 guard unchanged. GUI visual and final recovery/pressure pending.',
 'NEXT_EXECUTABLE_ACTION':'Run final production script recovery/abnormal-sidecar/pressure lifecycle matrix and tooltip/scope acceptance, fix observed defects and finalize author documentation without claiming multiplayer or crash atomicity',
 'INPUT_PATHS':[str(ROOT/'ai_docs/09_脚本数值系统/Array64脚本接口首轮接入.md'),str(A/'native_final/comparison.json')],
 'ACCEPTANCE_EVENT':'Production Array64 API lifecycle and explicit recovery/error/pressure examples pass with legacy regressions and truthful scope/tooltip limitations, ready for bounded singleplayer handoff'},ensure_ascii=False,indent=2),encoding='utf-8')
print('ARRAY_API_PACKAGE_VERIFIED')
