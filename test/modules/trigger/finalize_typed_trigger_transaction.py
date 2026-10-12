import hashlib,json,pathlib,shutil,subprocess,sys,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[3];TX=ROOT/'test/reports/20261012_variable64_transaction';N=TX/'numeric'
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
game={k:read(N/k/'comparison.json') for k in ['baseline','modified','rollback','final','pressure']}
assert game['baseline']['rows']==game['rollback']['rows']
assert game['baseline']['passed']==43 and len(game['baseline']['errors'])==106
assert all(game[k]['passed']==57 and game[k]['exit']==0 for k in ['modified','final','pressure'])
assert (N/'baseline/events.txt').read_bytes()==(N/'modified/events.txt').read_bytes()==(N/'rollback/events.txt').read_bytes()
pressure=read(N/'pressure/pressure.json');assert pressure['exit']==0
native=read(N/'native_final/result.json');assert native['exit']==0 and 'checks=27 passed=27 failed=0' in native['stdout']
bool_native=read(N/'bool_native_final/result.json');assert bool_native['exit']==0
raw={k:read(N/('raw_'+k)/'comparison.json') for k in ['baseline','modified','final','rollback']}
assert raw['final']['passed']==2049 and raw['final']['exit']==0
assert (N/'raw_baseline/inputs.txt').read_bytes()==(N/'raw_final/inputs.txt').read_bytes()==(N/'raw_rollback/inputs.txt').read_bytes()
assert (N/'raw_baseline/stdout.txt').read_bytes()==(N/'raw_rollback/stdout.txt').read_bytes()
assert sha(TX/'restore.numeric.dll')==sha(N/'hoi4_mod_plugin.BASELINE.dll')
assert sha(TX/'restore.numeric.c')==sha(N/'variable64.BASELINE.c')
stress=read(TX/'stress/post_typed/comparison.json');assert stress['passed']==516 and not stress['failed']
legacy=read(N/'legacy/comparison.json');assert len(legacy['rows'])==48 and not legacy['failures'] and not legacy['pollution']
scope=read(TX/'scope/post_typed/comparison.json');assert scope['exit']==0
boolean=read(TX/'trigger/post_typed/comparison.json');assert boolean['passed']==17 and not boolean['fixture_errors'] and boolean['registry_selfcheck']
old=read(TX/'VERIFICATION.txt')
if not (N/'pre_numeric_VERIFICATION.txt').exists():shutil.copyfile(TX/'VERIFICATION.txt',N/'pre_numeric_VERIFICATION.txt')
with zipfile.ZipFile(TX/'BASELINE.zip') as z:baseline={n:z.read(n) for n in z.namelist()}
with zipfile.ZipFile(TX/'MODIFIED_FILE.zip') as z:paths=set(z.namelist())
paths.update(['src/plugin/SDK_RVA/variable64/variable64.h','ai_docs/10_Trigger系统/数值块模板与Scope适配.md',
 'ai_docs/10_Trigger系统/多人环境顾虑与协调测试.md','test/modules/trigger/verify_typed_triggers.py',
 'test/modules/trigger/run_typed_trigger_pressure.py','test/modules/trigger/test_typed_trigger_native.py',
 'test/modules/trigger/finalize_typed_trigger_transaction.py','test/modules/effect/test_var64_stored_raw.py'])
new={p:(ROOT/p).read_bytes() for p in sorted(paths)}
def archive(p,items):
 with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in sorted(items.items()):
   i=zipfile.ZipInfo(n,(2026,10,12,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;z.writestr(i,b)
archive(TX/'MODIFIED_FILE.zip',new)
shutil.copyfile(TX/'BASELINE.zip',TX/'before/MODIFIED_FILE.zip');shutil.copyfile(TX/'MODIFIED_FILE.zip',TX/'after/MODIFIED_FILE.zip')
p=subprocess.run(['git','diff','--no-index','--binary','--','before/MODIFIED_FILE.zip','after/MODIFIED_FILE.zip'],cwd=TX,capture_output=True);assert p.returncode==1
(TX/'DIFF_FILE.patch').write_bytes(p.stdout)
shutil.copyfile(TX/'BASELINE.zip',TX/'reconstruct/MODIFIED_FILE.zip')
p=subprocess.run(['git','apply','-p2',str(TX/'DIFF_FILE.patch')],cwd=TX/'reconstruct',capture_output=True);assert p.returncode==0,p.stderr
assert sha(TX/'reconstruct/MODIFIED_FILE.zip')==sha(TX/'MODIFIED_FILE.zip')
shutil.copyfile(TX/'MODIFIED_FILE.zip',TX/'restored.zip')
p=subprocess.run(['C:/Program Files/Git/bin/bash.exe',str(TX/'ROLLBACK.sh'),str(TX/'restored.zip')],capture_output=True);assert p.returncode==0
assert sha(TX/'restored.zip')==sha(TX/'BASELINE.zip')
with zipfile.ZipFile(TX/'MODIFIED_FILE.zip') as z:
 assert z.testzip() is None
 for n in z.namelist():assert z.read(n)==(ROOT/n).read_bytes()
old['typed_trigger_extension']={'changed_symbols':['TriggerDef.parameterTemplate','TRG_VALUE_DEF','TRG_VARIABLE_DEF','TriggerScopeView','Trigger_ReadRawParameter','Trigger_CompareRaw','Trigger_EvaluateVariable','Var64_ReadStoredContainerRaw'],
 'single_player_priority':True,'multiplayer_tested':False,'game_three_state':{k:game[k] for k in ['baseline','modified','rollback']},
 'final_game':game['final'],'pressure':pressure,'native':native,'bool_native':bool_native,
 'raw_three_state':raw,'raw_read_inputs':str(N/'raw_final/inputs.txt'),'raw_literal_stdout':str(N/'raw_final/stdout.txt'),'raw_literal_stderr':str(N/'raw_final/stderr.txt'),
 'raw_rollback_hash_matches':True,'plugin_rollback_hash_matches':True,'plugin_baseline_sha256':sha(N/'hoi4_mod_plugin.BASELINE.dll'),
 'build':{'command':'MSBuild hoi4plugins.sln /p:Configuration=Release /p:Platform=x64 /v:minimal /nologo','exit':0,'stdout':(N/'build_guard.txt').read_text(encoding='utf-8',errors='replace'),'stderr':''},
 'scope_regression':scope,'bool_regression':boolean,'variable64_regression':{'checks':stress['checks'],'passed':stress['passed'],'failed':stress['failed']},
 'literal_game_commands':read(N/'legacy/commands.json'),
 'legacy_regression':{'checks':48,'passed':48,'pollution':legacy['pollution'],'failures':legacy['failures']},
 'math':read(N/'math/comparison.json'),'identity':read(N/'identity/result.json'),'language_stdout':(N/'language_console.txt').read_text(encoding='utf-8'),
 'package_patch_exact':True,'package_rollback_exact':True,
 'errors_retained':['Old hoi4-scope IDA worker unreachable; opened verified local database copy as hoi4-numeric with bundled open.ps1.',
 'IDA worker later unreachable when querying initializer flag; retained prior constructor evidence, confirmed behavior with final native/game checks.',
 'Baseline and rollback typed game commands exit 1 with 106 expected unknown-trigger errors; not counted as registered success.',
 'Initial raw overflow guard rejected six mathematically representable borrowed integer/fraction boundary encodings (2043/2049, exit 1); normalized boundary borrow before safe multiply, 2049/2049 exit 0.',
 'Pre-guard raw baseline and rollback have 26 failed overflow metadata checks, oracle exit 1; fixture process itself exits 0.'],
 'remaining':['multiplayer synchronization/rejoin/host swap','full dynamic/temp/random parameter matrix','full prefix-chain/savegame lifecycle matrix','persistent debt comparisons','custom parameter-aware variable64 tooltip rendering','UI visual validation','hot unload/multithreading/long-run']}
old['latest_modified_hashes']={n:hashlib.sha256(b).hexdigest() for n,b in new.items()}
(TX/'VERIFICATION.txt').write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8')
roles={}
for n in ['MODIFIED_FILE.zip','DIFF_FILE.patch','VERIFICATION.txt','ROLLBACK.sh']:
 p=TX/n;b=p.read_bytes();roles[n]={'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)};print(json.dumps(roles[n],ensure_ascii=False))
(TX/'artifact_hashes.json').write_text(json.dumps(roles,ensure_ascii=False,indent=2),encoding='utf-8')
(TX/'checkpoint.json').write_text(json.dumps({'ACTIVE_OBJECT':str(ROOT/'src/plugin/SDK_RVA/trigger/trigger_reg.c'),
 'LAST_CONFIRMED_RESULT':'Typed scalar/block triggers: real game 57/57, 1000 true/1000 false combinations, ROOT/PREV/FROM/global; native 27/27 plus 150 extreme compare cases; safe three-slot decoder 2049/2049; real DLL rollback reproduces 43/57 and 106 unknown-trigger errors; final modified deployment active',
 'NEXT_EXECUTABLE_ACTION':'Improve custom parameter-aware variable64 tooltip and extend single-player dynamic/temp/missing-variable and lifecycle cases before coordinating multiplayer tests',
 'INPUT_PATHS':[str(ROOT/'ai_docs/10_Trigger系统/数值块模板与Scope适配.md'),str(ROOT/'ai_docs/10_Trigger系统/多人环境顾虑与协调测试.md')],
 'ACCEPTANCE_EVENT':'Custom tooltip text represents full variable64 parameters and result correctly through native formatting, with no regression of readonly scope semantics'},ensure_ascii=False,indent=2),encoding='utf-8')
print('TYPED_TRIGGER_TRANSACTION_VERIFIED')
