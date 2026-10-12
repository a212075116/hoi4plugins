import hashlib,json,pathlib,shutil,subprocess,sys,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[3];TX=ROOT/'test/reports/20261012_variable64_transaction';T=TX/'tooltip'
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
game=read(T/'verified_lifecycle/comparison.json');assert game['passed']==20 and game['exit']==0 and game['reload_ok']
native={k:read(T/('native_'+k)/'result.json') for k in ['baseline_final','final','rollback']}
assert 'checks=16 passed=16 failed=0' in native['final']['stdout'] and native['final']['exit']==0
assert native['baseline_final']['stdout']==native['rollback']['stdout'] and native['baseline_final']['exit']==native['rollback']['exit']==1
assert sha(T/'restore.tooltip.c')==sha(T/'trigger_reg.BASELINE.c')
typed=read(T/'typed_native/result.json');boolean_native=read(T/'bool_native/result.json');assert typed['exit']==boolean_native['exit']==0
pressure=read(TX/'numeric/post_tooltip/pressure.json');assert pressure['exit']==0
typed_game=read(TX/'numeric/post_tooltip/comparison.json');assert typed_game['passed']==57
scope=read(TX/'scope/post_tooltip/comparison.json');assert scope['exit']==0
boolean=read(TX/'trigger/post_tooltip/comparison.json');assert boolean['passed']==17 and not boolean['fixture_errors']
legacy=read(T/'legacy/comparison.json');assert len(legacy['rows'])==48 and not legacy['failures'] and not legacy['pollution']
old=read(TX/'VERIFICATION.txt')
if not (T/'pre_tooltip_VERIFICATION.txt').exists():shutil.copyfile(TX/'VERIFICATION.txt',T/'pre_tooltip_VERIFICATION.txt')
with zipfile.ZipFile(TX/'MODIFIED_FILE.zip') as z:paths=set(z.namelist())
paths.update(['ai_docs/10_Trigger系统/Tooltip与单人生命周期验证.md','test/modules/trigger/test_typed_tooltip_native.py',
 'test/modules/trigger/verify_trigger_tooltip_lifecycle.py','test/modules/trigger/finalize_tooltip_transaction.py',
 'test/modules/trigger/typed_tooltip_l_english_reference.yml','test/modules/trigger/typed_tooltip_l_simp_chinese_reference.yml'])
new={p:(ROOT/p).read_bytes() for p in sorted(paths)}
with zipfile.ZipFile(TX/'MODIFIED_FILE.zip','w',zipfile.ZIP_DEFLATED) as z:
 for n,b in sorted(new.items()):
  i=zipfile.ZipInfo(n,(2026,10,12,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;z.writestr(i,b)
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
old['tooltip_extension']={'changed_symbols':['Trigger_TypedTooltip','Trigger_FormatRaw','Trigger_HasTemporaryOperand','Trigger_ReadRawParameter'],
 'native_three_state':native,'source_rollback_hash_matches':True,'source_baseline_sha256':sha(T/'trigger_reg.BASELINE.c'),
 'game_baseline_probe':read(T/'baseline_verified/comparison.json'),'game_correct_scope_probe':read(T/'scope_context/comparison.json'),
 'game_lifecycle':game,'write_tooltips':read(T/'verified_lifecycle/write_samples.json'),'reload_tooltips':read(T/'verified_lifecycle/reload_samples.json'),
 'literal_write_commands':read(T/'verified_lifecycle/write_commands.json'),'literal_reload_commands':read(T/'verified_lifecycle/reload_commands.json'),
 'saved_snapshot_sha256':sha(T/'verified_lifecycle/save_snapshot.hoi4'),
 'native_typed_regression':typed,'native_bool_regression':boolean_native,'typed_game':typed_game,'pressure':pressure,
 'scope':scope,'bool_game':boolean,'legacy':{'checks':48,'passed':48,'failures':legacy['failures'],'pollution':legacy['pollution']},
 'literal_regression_commands':read(T/'legacy/commands.json'),
 'build':{'command':'MSBuild hoi4plugins.sln /p:Configuration=Release /p:Platform=x64 /v:minimal /nologo','exit':0,'stdout':(T/'build_final.txt').read_text(encoding='utf-8',errors='replace'),'stderr':''},
 'package_patch_exact':True,'package_rollback_exact':True,'rollback_scope':'Actual production source compiled with controlled native dependencies and independent ZIP restoration; no live DLL rollback claimed for this stage.',
 'single_player_priority':True,'multiplayer_tested':False,
 'errors_retained':['Early probe read through closing bracket instead of native begin/end; empty captures, oracle exit 1.',
 'Optimized paths can bypass common wrapper; directly intercepted registered custom eval addresses and used callback scope.',
 'Text value initially stored at +16 (fallback key), not +48; mocked formatter shared bad assumption, while actual game showed empty parameters. Native binding evidence corrected both.',
 'Initial native tooltip fixture operator expectation for unavailable volatile input failed, 15/16 exit 1; retained. Preserved parsed comparison token without evaluating volatile parameters, 16/16 exit 0.',
 'Localisation log context misused as CEventScope: final round 14/20 and failed reload oracle despite valid save data; corrected to synchronous evaluate callback context, verified_lifecycle 20/20 with reload success.',
 'Persistent-first read wrongly shadowed native temporary value; baseline custom condition false vs native true. Delegated matching temp reads to native before three-slot lookup.'],
 'remaining':['mouse-hover/visual UI and long-running formatting','full Unicode UI localization validation','custom def.eval semantics require matching tooltip','instance tooltip= override','dynamic alias conflicts/arrays/nested random','all scope/prefix-chain persistence and hot load','persistent debt comparisons','multiplayer/rejoin/threading']}
old['latest_modified_hashes']={p:hashlib.sha256(b).hexdigest() for p,b in new.items()}
(TX/'VERIFICATION.txt').write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8')
roles={}
for n in ['MODIFIED_FILE.zip','DIFF_FILE.patch','VERIFICATION.txt','ROLLBACK.sh']:
 p=TX/n;b=p.read_bytes();roles[n]={'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)};print(json.dumps(roles[n],ensure_ascii=False))
(TX/'artifact_hashes.json').write_text(json.dumps(roles,ensure_ascii=False,indent=2),encoding='utf-8')
(TX/'checkpoint.json').write_text(json.dumps({'ACTIVE_OBJECT':str(ROOT/'src/plugin/SDK_RVA/trigger/trigger_reg.c'),
 'LAST_CONFIRMED_RESULT':'Custom raw tooltip 20/20 through real CEventScope/native formatting, native tooltip 16/16 with 1/16 baseline and rollback identical, native temp precedence fixed; fresh ttlife save/restart verified marker/big/negative/persistent shadow and tooltip; typed 57/57 plus 2000 combinations, Bool17/native22/typed27, scope12, legacy48 retained',
 'NEXT_EXECUTABLE_ACTION':'Extend single-player scope/prefix and dynamic alias/array boundaries, and validate Chinese tooltip/UI presentation without expanding multiplayer claims',
 'INPUT_PATHS':[str(ROOT/'ai_docs/10_Trigger系统/Tooltip与单人生命周期验证.md'),str(ROOT/'ai_docs/10_Trigger系统/多人环境顾虑与协调测试.md')],
 'ACCEPTANCE_EVENT':'A concrete additional boundary or presentation case is matched against native behavior and verified with preserved rollback evidence'},ensure_ascii=False,indent=2),encoding='utf-8')
print('TOOLTIP_TRANSACTION_VERIFIED')
