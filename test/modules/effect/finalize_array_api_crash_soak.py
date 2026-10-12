import hashlib,json,pathlib,shutil,subprocess,sys,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[3];TX=ROOT/'test/reports/20261012_variable64_transaction';A=TX/'api'
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
out=A/sys.argv[1];result=read(out/'comparison.json');assert result['exit']==0 and result['checks']==result['passed'] and result['alive']
assert sha(ROOT.parent/'hoi4_mod_plugin.dll')==result['dll_sha256']==sha(A/'hoi4_mod_plugin.MODIFIED.dll')
old=read(TX/'VERIFICATION.txt')
for path,expected in old['latest_modified_hashes'].items():
 if path.startswith('src/'):assert sha(ROOT/path)==expected,path
with zipfile.ZipFile(TX/'MODIFIED_FILE.zip') as z:paths=set(z.namelist())
paths.update(['test/modules/effect/verify_array64_api_crash_soak.py','test/modules/effect/finalize_array_api_crash_soak.py','ai_docs/09_脚本数值系统/Array64真实中断与定时持续运行验收.md'])
with zipfile.ZipFile(TX/'MODIFIED_FILE.zip','w',zipfile.ZIP_DEFLATED) as z:
 for n in sorted(paths):
  info=zipfile.ZipInfo(n,(2026,10,12,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,(ROOT/n).read_bytes())
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
 audit[label]={'command':p.args,'stdout':p.stdout.decode('utf-8'),'stderr':p.stderr.decode('utf-8'),'exit':p.returncode};print(label,audit[label]['stdout'].strip())
with zipfile.ZipFile(TX/'MODIFIED_FILE.zip') as z:
 assert z.testzip() is None
 for n in z.namelist():assert z.read(n)==(ROOT/n).read_bytes()
modes=['temp_written','before_receipt','partial_element'] if result['actual_forced_terminations'] else []
old['array_api_crash_soak_extension']={'symbol':'a64_store / Array64_JournalBegin / Array64_ShapeApply, instrumented process termination only',
 'runtime':result,'actual_crash_evidence':{m:read(out/(m+'_crash.json')) for m in modes},
 'literal_commands':{label:read(out/(label+'_commands.json')) for label in ['baseline','soak_save','soak_reload']+[m+'_restart' for m in modes]+[m+'_paired' for m in modes]},
 'soak_commands':read(out/'soak_commands.json'),'paired_soak_sidecars':read(out/'soak_paired_hashes.json'),'paired_soak_save_sha256':sha(out/'soak_save_save.hoi4'),
 'idle_control':read(out/'idle_control.json'),'resource_acceptance_complete':False,
 'orphan_cleanup':read(out/'orphan_cleanup.json') if modes else None,'prior_attempt_cleanup':{p:read(A/(p+'/orphan_cleanup.json')) for p in ['crash_soak_v2','crash_soak_v3']},
 'retained_host_errors':{p:(A/p).read_text(encoding='utf-8') for p in ['crash_soak_v1_console.txt','crash_soak_v2_console.txt','crash_soak_v3_console.txt']},
 'host_error_explanations':['v1: borrowed Frida retval object was reused; clone pointer before persisting it. No verified kill at that gate; restored exact original test sidecar.',
 'v2/v3: immediate tasklist/RPC completion is not a reliable death witness; use exact process handle WaitForSingleObject and GetExitCodeProcess, record before assertion. Earlier attempts not counted as completed matrix cases.',
 'The final harness may close a waiting host RPC only after independent OS death confirmation; such exceptions are not native crash diagnostics.'],
 'package_three_state':audit,'patch_reconstructs_exact_package':True,'package_rollback_exact':True,'production_source_changed':False,
 'limits':['180-second bounded event stress is not multi-hour soak, leak proof or campaign-time advancement','Instrumented kill points are not arbitrary crashes or power-loss/filesystem-durability proof','No game/save and journal joint atomicity','Native GUI access remains unavailable; no multiplayer acceptance']}
old.setdefault('array_api_crash_soak_runs',{})[out.name]=old['array_api_crash_soak_extension']
old['latest_modified_hashes']={n:sha(ROOT/n) for n in sorted(paths)}
(TX/'VERIFICATION.txt').write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8')
roles={}
for n in ['MODIFIED_FILE.zip','DIFF_FILE.patch','VERIFICATION.txt','ROLLBACK.sh']:
 p=TX/n;b=p.read_bytes();roles[n]={'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)};print(json.dumps(roles[n],ensure_ascii=False))
(TX/'artifact_hashes.json').write_text(json.dumps(roles,ensure_ascii=False,indent=2),encoding='utf-8')
(TX/'checkpoint.json').write_text(json.dumps({'ACTIVE_OBJECT':str(ROOT/'src/plugin/SDK_RVA/variable64/variable64.c'),
 'LAST_CONFIRMED_RESULT':f'Three instrumented real process-kill boundaries, old save/sidecar rejection and exact pair recovery, five-scope timed event stress {result["passed"]}/{result["checks"]}; {result["soak"]["operations"]} operations in {result["soak"]["elapsed_seconds"]:.2f}s; save/restart verified. Production DLL unchanged. Orphan temp observed and exact run-owned files archived/cleaned.',
 'NEXT_EXECUTABLE_ACTION':'Compare equal-count empty native events and balanced vanilla-array operations against Array64 from the new exact a64soak paired backup, tracking private bytes/handles. Diagnose resource growth before extending to multi-hour soak; do not repeat completed three kill gates or add features. GUI/power-loss/multiplayer remain unverified.',
 'INPUT_PATHS':[str(ROOT/'ai_docs/09_脚本数值系统/Array64真实中断与定时持续运行验收.md'),str(out/'comparison.json'),str(out/'soak_paired_hashes.json')],
 'ACCEPTANCE_EVENT':'Completed real process-termination boundaries and timed soak evidence delivered with unchanged production source and precise remaining limits'},ensure_ascii=False,indent=2),encoding='utf-8')
print('CRASH_SOAK_PACKAGE_VERIFIED')
