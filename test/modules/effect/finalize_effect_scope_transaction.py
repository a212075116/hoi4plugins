import pathlib,json,hashlib,subprocess,zipfile,shutil,sys
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
ROOT=pathlib.Path(__file__).resolve().parents[3];TX=ROOT/'test/reports/20261012_variable64_transaction';S=TX/'scope'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
comparison=read(S/'modified/comparison.json');assert comparison['exit']==0 and comparison['passed']==12
native={k:read(S/('native_'+k)/'result.json') for k in ['baseline','modified','rollback']}
assert all(v['exit']==0 and not v['stderr'] for v in native.values())
assert 'result_raw=2000000' in native['baseline']['stdout'] and 'result_raw=2500000' in native['modified']['stdout']
assert native['baseline']['stdout']==native['rollback']['stdout']
assert sha(S/'variable64.c.BASELINE')==sha(TX/'restore.scope.c')
stress=read(TX/'stress/post_scope/comparison.json');assert stress['passed']==516 and not stress['failed']
legacy=read(S/'legacy/comparison.json');assert not legacy['failures'] and not legacy['pollution'] and len(legacy['rows'])==48
old=read(TX/'VERIFICATION.txt');shutil.copyfile(TX/'VERIFICATION.txt',S/'pre_scope_VERIFICATION.txt')
with zipfile.ZipFile(TX/'BASELINE.zip') as z:baseline={n:z.read(n) for n in z.namelist()}
with zipfile.ZipFile(TX/'MODIFIED_FILE.zip') as z:paths=set(z.namelist())
added=['src/plugin/SDK_RVA/effect/'+n for n in ['effect_reg.h','effect_reg.c','effect_camera.c','effect_gamedate.c']]
for p in added:baseline.setdefault(p,(S/(pathlib.Path(p).name+'.BASELINE_git')).read_bytes())
paths.update(added)
paths.update(['ai_docs/08_Effect系统/注册器API.md','ai_docs/08_Effect系统/Scope与scoped操作数验证.md',
 'test/modules/effect/test_var64_identity.py','test/modules/effect/test_var64_scoped_operand.py',
 'test/modules/effect/verify_effect_scopes.py','test/modules/effect/finalize_effect_scope_transaction.py'])
new={p:(ROOT/p).read_bytes() for p in sorted(paths)}
def archive(p,items):
 with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:
  for n,b in sorted(items.items()):
   i=zipfile.ZipInfo(n,(2026,10,12,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;z.writestr(i,b)
archive(TX/'BASELINE.zip',baseline);archive(TX/'MODIFIED_FILE.zip',new)
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
old['scope_extension']={'changed_symbols':['EffectDef.supportedScopes','Effect_ScopeAny','Var64_ContainerAt','Var64_ReadStoredIn','Var64_ReadStoredOperandAt','Var64_TryDebtArithmetic','Var64_TryArithmetic','Var64_ClampDetour'],
 'baseline_game':read(S/'baseline/report.json'),'modified_game':read(S/'modified/report.json'),'modified_oracle':comparison,
 'native_three_state':native,'rollback_source_matches':True,'scope_baseline_sha256':sha(S/'variable64.c.BASELINE'),
 'build':{'exit':0,'stdout':(S/'build_clean.txt').read_text(encoding='utf-8',errors='replace'),'stderr':'','configuration':'Release|x64'},
 'math':read(S/'math/comparison.json'),'identity':read(S/'identity/result.json'),
 'language_stdout':(S/'language_console.txt').read_text(encoding='utf-8'),
 'stress':{'checks':stress['checks'],'passed':stress['passed'],'failed':stress['failed']},
 'legacy':{'checks':48,'passed':48,'pollution':legacy['pollution'],'failures':legacy['failures']},
 'package_patch_exact':True,'package_rollback_exact':True,
 'rollback_scope':'Independent source native fixture and ZIP restoration; no live-game rollback is claimed.',
 'errors_retained':['C4101 unused clamp locals in initial build; removed, clean build exit 0.',
 'Scope oracle regex initially consumed newlines, Decimal.InvalidOperation exit 1; changed capture to non-whitespace and reverified exit 0.',
 'docs-generator sibling tool-index.md absent, Get-Content exit 1; no dependency tool was needed for local Markdown.'],
 'remaining':['full scoped-prefix chain matrix','scope without a native variable container','persistent debt operands','multiplayer/multithreading/long-run','numeric/block triggers and typed Trigger scope adapter']}
old['latest_modified_hashes']={p:hashlib.sha256(b).hexdigest() for p,b in new.items()}
(TX/'VERIFICATION.txt').write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8')
roles={}
for n in ['MODIFIED_FILE.zip','DIFF_FILE.patch','VERIFICATION.txt','ROLLBACK.sh']:
 p=TX/n;b=p.read_bytes();roles[n]={'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)};print(json.dumps(roles[n],ensure_ascii=False))
(TX/'artifact_hashes.json').write_text(json.dumps(roles,ensure_ascii=False,indent=2),encoding='utf-8')
(TX/'checkpoint.json').write_text(json.dumps({'ACTIVE_OBJECT':str(ROOT/'src/plugin/SDK_RVA/variable64/variable64.c'),
 'LAST_CONFIRMED_RESULT':'Effect scope Any for global camera/date, native variable containers unchanged, ROOT/PREV/FROM/global scoped operands verified; scope oracle 12/12 and callback mask checks, variable64 516/516, legacy 48/48, native rollback 20/25/20',
 'NEXT_EXECUTABLE_ACTION':'Implement numeric/block trigger template and typed Trigger scope adapter using native Trigger context evidence, not Effect offsets',
 'INPUT_PATHS':[str(ROOT/'ai_docs/08_Effect系统/Scope与scoped操作数验证.md'),str(ROOT/'ai_docs/10_Trigger系统/注册器API与验证.md')],
 'ACCEPTANCE_EVENT':'Registered comparison trigger parses its parameter block and reads the intended native Trigger variable container'},ensure_ascii=False,indent=2),encoding='utf-8')
print('SCOPE_TRANSACTION_VERIFIED')
