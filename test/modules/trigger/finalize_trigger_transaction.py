import hashlib,json,pathlib,shutil,subprocess,sys,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[3];TX=ROOT/'test/reports/20261012_variable64_transaction';T=TX/'trigger'
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
basic=json.loads((T/'canonical/comparison.json').read_text(encoding='utf-8'))
stress=json.loads((T/'stress/comparison.json').read_text(encoding='utf-8'))
var=json.loads((TX/'stress/post_trigger/comparison.json').read_text(encoding='utf-8'))
legacy=json.loads((T/'final_regression/comparison.json').read_text(encoding='utf-8'))
native=json.loads((T/'native_final/result.json').read_text(encoding='utf-8'))
tips=json.loads((T/'tooltip.json').read_text(encoding='utf-8'))
assert basic['passed']==17 and basic['registry_selfcheck']
assert stress['passed']==17 and stress['stress_ok'] and stress['registry_selfcheck']
assert var['passed']==516 and not var['failed']
assert not legacy['failures'] and not legacy['pollution']
assert native['exit']==0 and 'checks=22 passed=22 failed=0' in native['stdout']
assert len(tips)==3 and all('Plugin ' in x['text'] for x in tips)
(T/'pre_trigger_VERIFICATION.txt').write_bytes((TX/'VERIFICATION.txt').read_bytes())
old=json.loads((TX/'VERIFICATION.txt').read_text(encoding='utf-8'))
shutil.copyfile(TX/'BASELINE.zip',T/'pre_trigger_BASELINE.zip')
with zipfile.ZipFile(TX/'BASELINE.zip') as z:original={p:z.read(p) for p in z.namelist()}
original.update({'src/plugin/plugin_main.c':(T/'plugin_main.c.BASELINE').read_bytes(),'src/plugin/plugin.vcxproj':(T/'plugin.vcxproj.BASELINE').read_bytes()})
with zipfile.ZipFile(TX/'MODIFIED_FILE.zip') as z:paths=z.namelist()
paths+=['src/plugin/plugin_main.c','src/plugin/plugin.vcxproj','src/plugin/SDK_RVA/trigger/trigger_reg.h','src/plugin/SDK_RVA/trigger/trigger_reg.c','src/plugin/SDK_RVA/trigger/trigger_demo.c',
 'ai_docs/10_Trigger系统/注册器API与验证.md','ai_docs/09_脚本数值系统/变量系统类与函数.md',
 'test/modules/trigger/verify_trigger_registry.py','test/modules/trigger/test_trigger_registry_native.py','test/modules/trigger/probe_trigger_tooltip.py','test/modules/trigger/audit_trigger_project.py','test/modules/trigger/finalize_trigger_transaction.py']
new={p:(ROOT/p).read_bytes() for p in sorted(set(paths))}
def archive(path,items):
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
  for name,b in sorted(items.items()):
   i=zipfile.ZipInfo(name,(2026,10,12,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;z.writestr(i,b)
archive(TX/'BASELINE.zip',original);archive(TX/'MODIFIED_FILE.zip',new)
shutil.copyfile(TX/'BASELINE.zip',TX/'before/MODIFIED_FILE.zip');shutil.copyfile(TX/'MODIFIED_FILE.zip',TX/'after/MODIFIED_FILE.zip')
p=subprocess.run(['git','diff','--no-index','--binary','--','before/MODIFIED_FILE.zip','after/MODIFIED_FILE.zip'],cwd=TX,capture_output=True);assert p.returncode==1
(TX/'DIFF_FILE.patch').write_bytes(p.stdout)
shutil.copyfile(TX/'BASELINE.zip',TX/'reconstruct/MODIFIED_FILE.zip')
p=subprocess.run(['git','apply','-p2',str(TX/'DIFF_FILE.patch')],cwd=TX/'reconstruct',capture_output=True);assert p.returncode==0,p.stderr
assert (TX/'reconstruct/MODIFIED_FILE.zip').read_bytes()==(TX/'MODIFIED_FILE.zip').read_bytes()
shutil.copyfile(TX/'MODIFIED_FILE.zip',TX/'restored.zip')
p=subprocess.run(['C:/Program Files/Git/bin/bash.exe',str(TX/'ROLLBACK.sh'),str(TX/'restored.zip')],capture_output=True);assert p.returncode==0
assert (TX/'restored.zip').read_bytes()==(TX/'BASELINE.zip').read_bytes()
with zipfile.ZipFile(TX/'MODIFIED_FILE.zip') as z:
 assert z.testzip() is None
 for name in z.namelist():assert z.read(name)==(ROOT/name).read_bytes()
old['trigger_extension']={'changed_symbols':['Trigger_RegistryRegister','Trigger_RegistryRegisterAll','Trigger_RegistryReady','Trigger_EvaluateBool','TRG_BOOL_DEF','TriggerDemo_Register'],
 'baseline_game':json.loads((T/'baseline/comparison.json').read_text(encoding='utf-8')),'basic_game':basic,'startup_stress_game':stress,'native_api':native,'tooltip_live':tips,
 'project_three_state':json.loads((T/'project_three_state.json').read_text(encoding='utf-8')),
 'project_baseline_hashes':{name:hashlib.sha256((T/(name+'.BASELINE')).read_bytes()).hexdigest() for name in ['plugin_main.c','plugin.vcxproj']},
 'variable64_post_trigger':{'checks':var['checks'],'passed':var['passed'],'failed':len(var['failed'])},'legacy_post_trigger':{'checks':len(legacy['rows']),'passed':48,'pollution':len(legacy['pollution'])},
 'rollback_scope':'Startup project integration checked in independent parseable ZIP; live rollback behavior is not claimed.',
 'trigger_rollback_package_hash_matches':(TX/'restore.trigger.zip').read_bytes()==(TX/'TRIGGER_BASELINE.zip').read_bytes(),
 'full_package_rollback_hash_matches':True,'binary_patch_reconstructs_exact_modified':True,
 'remaining':['numeric/block trigger parameters','typed trigger-scope adapters','variable64 comparisons','hot registration/unload','multithreading','visual UI validation'],
 'errors_retained':['Bundled IDA open initially lacked IDADIR; explicit configured path corrected it.',
 'One build command yielded before deployment; old deployed DLL identified by unequal hashes, then build completion awaited and phase restarted.',
 'Build session store received undefined session_id for a completed command; guarded store, no project bytes affected.',
 'Missing stdio declaration for _snprintf_s produced C4013; added header, final build clean.',
 'Initial static token-name scan assumed std::string at +8; real runtime record disproved it. Removed name-layout reads; canonical native token id and static integer id checks passed real selfcheck.',
 'Early selfcheck allowed always before builtin insertion; reserved canonical ids and existing entry rejection corrected, 3/3 unchanged.',
 'IDA worker later unreachable; retained static/runtime evidence, did not treat missing decompile as confirmation.']}
old['latest_modified_hashes']={p:hashlib.sha256(b).hexdigest() for p,b in new.items()}
(TX/'VERIFICATION.txt').write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8')
roles={}
for n in ['MODIFIED_FILE.zip','DIFF_FILE.patch','VERIFICATION.txt','ROLLBACK.sh']:
 p=TX/n;b=p.read_bytes();roles[n]={'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)};print(json.dumps(roles[n],ensure_ascii=False))
(TX/'artifact_hashes.json').write_text(json.dumps(roles,ensure_ascii=False,indent=2),encoding='utf-8')
(TX/'checkpoint.json').write_text(json.dumps({'ACTIVE_OBJECT':str(ROOT/'src/plugin/SDK_RVA/trigger/trigger_reg.c'),'LAST_CONFIRMED_RESULT':'Bool registrar: 17/17 real conditions, 22/22 native API, 3 native localized tooltips, 256 startup aliases/259 total, 2000 repeated combinations; variable64 516/516 and legacy 48/48 preserved','NEXT_EXECUTABLE_ACTION':'Design numeric/block trigger template and typed trigger scope adapter before adding variable64 comparisons','INPUT_PATHS':[str(ROOT/'ai_docs/10_Trigger系统/注册器API与验证.md'),str(T/'stress/comparison.json')],'ACCEPTANCE_EVENT':'A registered comparison trigger consumes correctly parsed parameters and reads the correct trigger scope without borrowing Effect offsets'},ensure_ascii=False,indent=2),encoding='utf-8')
print('TRIGGER_TRANSACTION_VERIFIED')
