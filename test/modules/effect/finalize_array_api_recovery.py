import hashlib,json,pathlib,shutil,subprocess,sys,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[3];TX=ROOT/'test/reports/20261012_variable64_transaction';A=TX/'api'
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
phase=sys.argv[1];result=read(A/phase/'comparison.json')
assert result['exit']==0 and result['checks']==result['passed'] and result['alive']
assert read(A/'empty_api_tooltips/comparison.json')['exit']==0
assert all(read(A/('empty_'+p+'/result.json'))['exit']==0 for p in ['registry','tooltip','boundary'])
assert sha(ROOT/'src/plugin/SDK_RVA/variable64/variable64.c')=='ec54864342e9e8811aaea73eb7ef66ed5f4f9328a7083854120f190880755c1e'
deployed=ROOT.parent/'hoi4_mod_plugin.dll';assert sha(deployed)==result['dll_sha256']==sha(ROOT/'build/Release/hoi4_mod_plugin.dll')
old=read(TX/'VERIFICATION.txt')
if not (A/'hoi4_mod_plugin.API_FIRST_ROUND.dll').exists():shutil.copyfile(A/'hoi4_mod_plugin.MODIFIED.dll',A/'hoi4_mod_plugin.API_FIRST_ROUND.dll')
shutil.copyfile(deployed,A/'hoi4_mod_plugin.MODIFIED.dll')
with zipfile.ZipFile(TX/'MODIFIED_FILE.zip') as z:paths=set(z.namelist())
paths.update(['test/modules/effect/verify_array64_api_recovery.py','test/modules/effect/test_array64_group_native.py','test/modules/effect/finalize_array_api_recovery.py','ai_docs/09_脚本数值系统/Array64恢复与压力首轮验收.md',
 'test/reports/20261012_variable64_transaction/api/native_array_readonly.EMPTY_BASELINE.c','test/reports/20261012_variable64_transaction/api/array64_group_readonly.EMPTY_BASELINE.c'])
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
old['array_api_extension']['historical_dll_archive']=str(A/'hoi4_mod_plugin.API_FIRST_ROUND.dll')
old['array_api_recovery_extension']={'symbol':'na_empty_table / na_lookup / ag_inventory','native_empty_header_evidence':read(A/'empty_container_baseline/headers.json'),'three_state':read(A/'empty_three_state.json'),
 'real_api_lifecycle':result,'native_journal_regression':read(A/'journal_empty_modified/result.json'),'package_three_state':audit,
 'native_tooltips':read(A/'empty_api_tooltips/comparison.json'),'legacy_fixtures':{p:read(A/('empty_'+p+'/result.json')) for p in ['registry','tooltip','boundary']},
 'build_stdout':(A/'build_empty_corrected.stdout.txt').read_text(encoding='utf-8'),'build_stderr':(A/'build_empty_corrected.stderr.txt').read_text(encoding='utf-8'),'build_exit':0,
 'modified_dll_sha256':sha(deployed),'fixture_commands':{p:read(A/phase/(p+'_commands.json')) for p in ['setup','normal','missing','truncated','checksum','foreign','oversize','inject','recover','pressure','reload','pressure_reload']},
 'retained_errors':{p:(A/p).read_text(encoding='utf-8') for p in ['recovery_v1_console.txt','recovery_v2_console.txt','empty_baseline_console.txt']},
 'error_explanations':['v1: native empty role scope rejected; real defect','v2: project-only MSBuild emitted into src/plugin/build, deployed older build/Release; corrected SolutionDir and verified deployed hash','probe first attempt GBK decoding exception; corrected explicit UTF-8, captured same fresh session'],
 'package_rollback_exact':True,'patch_reconstructs_exact_package':True,'limits':['Simulated persisted interrupted append, not a forced process crash','No GUI hover or localized result-word visual acceptance','No multiplayer, automatic save fork recognition, or joint save/sidecar atomicity','Bounded 32 cycles per scope, not hours-long soak']}
old['latest_modified_hashes']={n:sha(ROOT/n) for n in sorted(paths)}
(TX/'VERIFICATION.txt').write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8')
roles={}
for n in ['MODIFIED_FILE.zip','DIFF_FILE.patch','VERIFICATION.txt','ROLLBACK.sh']:
 p=TX/n;b=p.read_bytes();roles[n]={'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)};print(json.dumps(roles[n],ensure_ascii=False))
(TX/'artifact_hashes.json').write_text(json.dumps(roles,ensure_ascii=False,indent=2),encoding='utf-8')
(TX/'checkpoint.json').write_text(json.dumps({'ACTIVE_OBJECT':str(ROOT/'src/plugin/SDK_RVA/variable64/variable64.c'),
 'LAST_CONFIRMED_RESULT':f'Native empty sentinel fixed; unit2091/2091 and journal244/244; public recovery/file anomaly/interrupted append save/restart/pressure {result["passed"]}/{result["checks"]}; 5 scopes32 cycles each and4096 boundary; no GUI/forced crash/multiplayer acceptance.',
 'NEXT_EXECUTABLE_ACTION':'Extend public recovery to wrong receipt/ownership and saved-sidecar pairing lifecycle; verify tooltip visual only through supported UI access, or report that concrete limitation; finalize bounded singleplayer author handoff',
 'INPUT_PATHS':[str(ROOT/'ai_docs/09_脚本数值系统/Array64恢复与压力首轮验收.md'),str(A/phase/'comparison.json')],
 'ACCEPTANCE_EVENT':'Additional public receipt/ownership lifecycle checks observed, handoff scope accurately states bounded pressure and unavailable visual verification'},ensure_ascii=False,indent=2),encoding='utf-8')
print('RECOVERY_PACKAGE_VERIFIED')
