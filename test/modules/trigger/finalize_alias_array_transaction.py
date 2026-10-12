import hashlib,json,pathlib,shutil,subprocess,sys,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[3];TX=ROOT/'test/reports/20261012_variable64_transaction';B=TX/'boundary'
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
baseline=read(B/'baseline/comparison.json');modified=read(B/'modified/comparison.json');assert baseline['passed']==0 and modified['passed']==6 and modified['exit']==0
assert (B/'baseline/events.txt').read_bytes()==(B/'modified/events.txt').read_bytes()
native={k:read(B/('native_'+k)/'result.json') for k in ['baseline','modified','rollback']}
assert native['baseline']['stdout']==native['rollback']['stdout'] and native['baseline']['exit']==native['rollback']['exit']==1
assert native['modified']['exit']==0 and 'checks=8 passed=8 failed=0' in native['modified']['stdout']
for role,restore in [('trigger_reg.BASELINE.c','restore.boundary-trigger.c'),('variable64.BASELINE.c','restore.boundary-variable.c')]:assert sha(B/role)==sha(B/restore)
setter=read(TX/'setter/post_boundary/comparison.json');assert setter['passed']==57 and setter['exit']==0
tooltip=read(TX/'tooltip/post_boundary/comparison.json');assert tooltip['passed']==20 and tooltip['exit']==0
pressure=read(TX/'numeric/post_boundary/pressure.json');assert pressure['exit']==0
scope=read(TX/'scope/post_boundary/comparison.json');assert scope['exit']==0
boolean=read(TX/'trigger/post_boundary/comparison.json');assert boolean['passed']==17 and not boolean['fixture_errors']
legacy=read(B/'legacy/comparison.json');assert len(legacy['rows'])==48 and not legacy['failures'] and not legacy['pollution']
old=read(TX/'VERIFICATION.txt')
if not (B/'pre_boundary_VERIFICATION.txt').exists():shutil.copyfile(TX/'VERIFICATION.txt',B/'pre_boundary_VERIFICATION.txt')
with zipfile.ZipFile(TX/'MODIFIED_FILE.zip') as z:paths=set(z.namelist())
paths.update(['ai_docs/10_Trigger系统/动态同名与数组隔离验证.md','test/modules/trigger/test_alias_array_native.py',
 'test/modules/trigger/verify_alias_array_boundary.py','test/modules/trigger/finalize_alias_array_transaction.py'])
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
old['alias_array_extension']={'changed_symbols':['Trigger_HasDynamicBinding','Trigger_ReadRawParameter','Var64_ResolveGameVariableEx','Var64_ReadNameOnly','Var64_ReadOperandNameAt'],
 'game_baseline':baseline,'game_modified':modified,'literal_game_commands':{'baseline':(B/'baseline/command.txt').read_text(encoding='utf-8'),'modified':(B/'modified/command.txt').read_text(encoding='utf-8')},
 'native_three_state':native,'source_rollback_hash_matches':True,'baseline_hashes':{n:sha(B/n) for n in ['trigger_reg.BASELINE.c','variable64.BASELINE.c']},
 'descriptor_probe':read(B/'descriptor_probe.json'),'native_descriptor_values':read(B/'descriptor_values.json'),
 'indexed64_supported':False,'indexed64_policy':'Reject before mutation, preserve native array and same-name scalar; native index reads are delegated, not interpreted as scalar three-slot.',
 'explicit_prefix_policy':'CCheckVariable parses bare and var-prefixed tested dynamic alias identically; both preserve native binding priority.',
 'setter_regression':{'checks':57,'passed':57,'marker_ok':setter['marker_ok']},'chinese_tooltip':tooltip,'pressure':pressure,'scope':scope,'bool_game':boolean,
 'native_typed':read(B/'typed_native/result.json'),'native_tooltip':read(B/'tooltip_native/result.json'),'native_bool':read(B/'bool_native/result.json'),'identity':read(B/'identity/result.json'),
 'legacy':{'checks':48,'passed':48,'failures':legacy['failures'],'pollution':legacy['pollution']},'literal_regression_commands':read(B/'legacy/commands.json'),
 'build':{'command':'MSBuild hoi4plugins.sln /p:Configuration=Release /p:Platform=x64 /v:minimal /nologo','exit':0,'stdout':(B/'build.txt').read_text(encoding='utf-8',errors='replace'),'stderr':''},
 'package_patch_exact':True,'package_rollback_exact':True,'rollback_scope':'Actual source native fixture against controlled dependencies and ZIP restoration; no live DLL rollback claimed.',
 'errors_retained':['First patch matched a nonunique condition, then failed context; atomic tool failure, corrected full context.',
 'Initial oracle assumed var: bypasses native dynamic binding in CCheckVariable; observed identical descriptors/native raw values disproved it. Preserved initial_oracle and corrected comparison using original captured inputs.',
 'Modified process finished with old in-memory oracle exit 1; reverified unchanged captured input with corrected oracle, exit 0.'],
 'remaining':['full indexed variable64 protocol/storage/insert/delete/serialization','all dynamic aliases/prefix chains','mixed indexed targets with64 operands','UI mouse-hover/threading/multiplayer']}
old['latest_modified_hashes']={p:hashlib.sha256(b).hexdigest() for p,b in new.items()}
(TX/'VERIFICATION.txt').write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8')
roles={}
for n in ['MODIFIED_FILE.zip','DIFF_FILE.patch','VERIFICATION.txt','ROLLBACK.sh']:
 p=TX/n;b=p.read_bytes();roles[n]={'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)};print(json.dumps(roles[n],ensure_ascii=False))
(TX/'artifact_hashes.json').write_text(json.dumps(roles,ensure_ascii=False,indent=2),encoding='utf-8')
(TX/'checkpoint.json').write_text(json.dumps({'ACTIVE_OBJECT':str(ROOT/'src/plugin/SDK_RVA/variable64/variable64.c'),
 'LAST_CONFIRMED_RESULT':'Native dynamic priority and scalar/array isolation:6/6 game; native3/8->8/8->3/8 rollback exact; indexed64 writes rejected before mutation; setter57 with reload, Chinese tooltip20, typed57/2000 combinations, scope12, Bool17/legacy48 retained',
 'NEXT_EXECUTABLE_ACTION':'Design a separate explicit indexed-variable64 representation before enabling array writes; first document element identity, auxiliary naming and lifecycle invariants',
 'INPUT_PATHS':[str(ROOT/'ai_docs/10_Trigger系统/动态同名与数组隔离验证.md'),str(ROOT/'ai_docs/09_脚本数值系统/同名变量最后设置者规则.md')],
 'ACCEPTANCE_EVENT':'An explicit array64 design and executable element-isolation test prevents scalar aliasing and preserves native insert/delete/save semantics'},ensure_ascii=False,indent=2),encoding='utf-8')
print('ALIAS_ARRAY_TRANSACTION_VERIFIED')
