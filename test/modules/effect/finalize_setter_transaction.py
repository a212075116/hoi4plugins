import hashlib,json,pathlib,shutil,subprocess,sys,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[3];TX=ROOT/'test/reports/20261012_variable64_transaction';S=TX/'setter'
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
baseline=read(S/'baseline_verified/comparison.json');modified=read(S/'modified/comparison.json')
assert baseline['passed']==45 and baseline['checks']==47 and {r['key'] for r in baseline['failed']}=={'debt.native_reset','debt.promote_then_native'}
assert modified['passed']==modified['checks']==57 and modified['exit']==0 and modified['marker_ok']
assert (S/'baseline_verified/events.txt').read_bytes()==(S/'modified/events.txt').read_bytes()
native={k:read(S/('native_'+k)/'result.json') for k in ['baseline','modified','rollback']}
assert native['baseline']['stdout']==native['rollback']['stdout'] and native['baseline']['exit']==native['rollback']['exit']==1
assert native['modified']['exit']==0 and 'checks=9 passed=9 failed=0' in native['modified']['stdout']
assert (S/'restore.setter.c').read_bytes()==(S/'variable64.BASELINE.c').read_bytes()
chinese=read(TX/'tooltip/chinese_after_setter/comparison.json');assert chinese['passed']==20 and chinese['exit']==0
chinese_samples=read(TX/'tooltip/chinese_after_setter/write_samples.json')
assert all(('半值比较' if r['tag']=='scalar' else '64 位变量比较') in r['normal'] for r in chinese_samples)
pressure=read(TX/'numeric/post_setter/pressure.json');assert pressure['exit']==0
scope=read(TX/'scope/post_setter/comparison.json');assert scope['exit']==0
boolean=read(TX/'trigger/post_setter/comparison.json');assert boolean['passed']==17 and not boolean['fixture_errors']
legacy=read(S/'legacy/comparison.json');assert len(legacy['rows'])==48 and not legacy['failures'] and not legacy['pollution']
old=read(TX/'VERIFICATION.txt')
if not (S/'pre_setter_VERIFICATION.txt').exists():shutil.copyfile(TX/'VERIFICATION.txt',S/'pre_setter_VERIFICATION.txt')
with zipfile.ZipFile(TX/'MODIFIED_FILE.zip') as z:paths=set(z.namelist())
paths.update(['ai_docs/09_脚本数值系统/同名变量最后设置者规则.md','test/modules/effect/verify_setter_ownership.py',
 'test/modules/effect/test_setter_debt_native.py','test/modules/effect/finalize_setter_transaction.py'])
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
with zipfile.ZipFile(TX/'MODIFIED_FILE.zip') as z:
 assert z.testzip() is None
 for n in z.namelist():assert z.read(n)==(ROOT/n).read_bytes()
old['setter_extension']={'changed_symbols':['Var64_DoSetVariable64','Var64_GameSyntaxDetour','Var64_ResetDebtForSet'],
 'rule':'Last valid setter in the same resolved container/name owns native vs persistent three-slot representation; prior process-local debt is discarded on reassignment.',
 'game_baseline':baseline,'game_modified':modified,'native_three_state':native,'source_rollback_hash_matches':True,'source_baseline_sha256':sha(S/'variable64.BASELINE.c'),
 'write_commands':read(S/'modified/write_commands.json'),'reload_commands':read(S/'modified/reload_commands.json'),'save_snapshot_sha256':sha(S/'modified/save_snapshot.hoi4'),
 'write_identity_snapshots':read(S/'modified/write_samples.json'),'reload_identity_snapshots':read(S/'modified/reload_samples.json'),
 'chinese_tooltip':chinese,'chinese_samples':chinese_samples,'pressure':pressure,'scope':scope,'bool_game':boolean,
 'legacy':{'checks':48,'passed':48,'failures':legacy['failures'],'pollution':legacy['pollution']},'literal_regression_commands':read(S/'legacy/commands.json'),
 'identity':read(S/'identity/result.json'),'math':read(S/'math/comparison.json'),'decoder':read(S/'decoder/comparison.json'),
 'typed_native':read(S/'typed_native/result.json'),'tooltip_native':read(S/'tooltip_native/result.json'),
 'build':{'command':'MSBuild hoi4plugins.sln /p:Configuration=Release /p:Platform=x64 /v:minimal /nologo','exit':0,'stdout':(S/'build.txt').read_text(encoding='utf-8',errors='replace'),'stderr':''},
 'package_patch_exact':True,'package_rollback_exact':True,'rollback_scope':'Production setter source compiled against controlled native writes/debt fixtures and independent ZIP restoration; no live-game DLL rollback claimed.',
 'errors_retained':['Initial readonly sampler wrapped Robin Hood table at mask; production uses contiguous spill, causing three identity false negatives. Corrected sampler, baseline_verified 45/47 with only two real debt failures.',
 'Native baseline and rollback have four failed debt-reset checks (5/9, exit 1); changed source 9/9 exit 0.',
 'One supplemental Chinese JSON inspection used default GBK and failed decoding (exit 1); repeated with explicit UTF-8, 20/20 Chinese strings confirmed.'],
 'remaining':['UI mouse-hover/visual verification','invalid/native partial-write and allocation failures','dynamic alias/array/all scope-prefix chains','dedicated add64 and debt interactions','hot load/threading/multiplayer','persistent debt save/load']}
old['latest_modified_hashes']={p:hashlib.sha256(b).hexdigest() for p,b in new.items()}
(TX/'VERIFICATION.txt').write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8')
roles={}
for n in ['MODIFIED_FILE.zip','DIFF_FILE.patch','VERIFICATION.txt','ROLLBACK.sh']:
 p=TX/n;b=p.read_bytes();roles[n]={'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)};print(json.dumps(roles[n],ensure_ascii=False))
(TX/'artifact_hashes.json').write_text(json.dumps(roles,ensure_ascii=False,indent=2),encoding='utf-8')
(TX/'checkpoint.json').write_text(json.dumps({'ACTIVE_OBJECT':str(ROOT/'src/plugin/SDK_RVA/variable64/variable64.c'),
 'LAST_CONFIRMED_RESULT':'Last-setter rule: five native containers, 320 alternating writes, 47 immediate+10 reload checks=57/57; old debt cleared on native and64 setters; native three-state5/9->9/9->5/9 with exact restored source; Chinese tooltip20/20; typed57+2000 combinations, scope12, Bool17, legacy48 retained',
 'NEXT_EXECUTABLE_ACTION':'Extend single-player dynamic alias/array and scope-prefix boundaries before UI visual/multiplayer coordination',
 'INPUT_PATHS':[str(ROOT/'ai_docs/09_脚本数值系统/同名变量最后设置者规则.md'),str(ROOT/'ai_docs/10_Trigger系统/Tooltip与单人生命周期验证.md')],
 'ACCEPTANCE_EVENT':'A concrete new boundary is compared with native semantics, with rollback evidence and no regression of setter ownership/readonly comparisons'},ensure_ascii=False,indent=2),encoding='utf-8')
print('SETTER_TRANSACTION_VERIFIED')
