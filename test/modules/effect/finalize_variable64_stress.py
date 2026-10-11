"""Extend the existing transaction; preserve its baseline and previous verification."""
import difflib,hashlib,json,pathlib,shutil,subprocess,sys,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[3]
TX=ROOT/'test/reports/20261012_variable64_transaction'
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
final=json.loads((TX/'stress/final/comparison.json').read_text(encoding='utf-8'))
assert final['checks']==516 and final['passed']==516 and not final['failed']
legacy=json.loads((TX/'stress/legacy/comparison.json').read_text(encoding='utf-8'))
assert len(legacy['rows'])==48 and not legacy['failures'] and not legacy['pollution']
assert (TX/'variable64.STRESS_BASELINE.c').read_bytes()==(TX/'variable64.rollback.stress.c').read_bytes()
assert (ROOT/'src/plugin/SDK_RVA/variable64/variable64.c').read_bytes()==(TX/'variable64.STRESS_MODIFIED.c').read_bytes()
(TX/'pre_stress_VERIFICATION.txt').write_bytes((TX/'VERIFICATION.txt').read_bytes())
previous=json.loads((TX/'VERIFICATION.txt').read_text(encoding='utf-8'))
with zipfile.ZipFile(TX/'BASELINE.zip') as z:original={p:z.read(p) for p in z.namelist()}
with zipfile.ZipFile(TX/'MODIFIED_FILE.zip') as z:paths=z.namelist()
paths+=['ai_docs/09_脚本数值系统/读档身份与抗压验证.md','test/docs/README.md',
        'test/modules/effect/stress_variable64.py','test/modules/effect/test_var64_identity.py',
        'test/modules/effect/test_var64_raw_math.py','test/modules/effect/verify_variable64_reproduction.py',
        'test/modules/effect/finalize_variable64_stress.py','test/archive/stress_readonly_diagnostic.py']
paths=sorted(set(paths))
new={p:(ROOT/p).read_bytes() for p in paths}
# The supplemental baseline is the user-approved commit before this turn's fixes.
stress_base={p:subprocess.run(['git','show','0d24c95:'+p],cwd=ROOT,capture_output=True).stdout for p in paths}
(TX/'stress_baseline_hashes.json').write_text(json.dumps({p:hashlib.sha256(b).hexdigest() for p,b in stress_base.items() if b},indent=2),encoding='utf-8')
def archive(p,items):
 with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:
  for name,b in sorted(items.items()):
   info=zipfile.ZipInfo(name,(2026,10,12,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,b)
archive(TX/'MODIFIED_FILE.zip',new)
shutil.copyfile(TX/'BASELINE.zip',TX/'before/MODIFIED_FILE.zip')
shutil.copyfile(TX/'MODIFIED_FILE.zip',TX/'after/MODIFIED_FILE.zip')
p=subprocess.run(['git','diff','--no-index','--binary','--','before/MODIFIED_FILE.zip','after/MODIFIED_FILE.zip'],cwd=TX,capture_output=True)
assert p.returncode==1
(TX/'DIFF_FILE.patch').write_bytes(p.stdout)
(TX/'docs.diff').write_text(''.join(''.join(difflib.unified_diff(original.get(p,b'').decode('utf-8-sig').splitlines(True),b.decode('utf-8-sig').splitlines(True),fromfile=p,tofile=p)) for p,b in new.items()),encoding='utf-8')
records=[]
def cmd(label,args,cwd=None):
 p=subprocess.run(args,cwd=cwd,capture_output=True)
 record={'label':label,'command':args,'stdout':p.stdout.decode('utf-8',errors='replace'),'stderr':p.stderr.decode('utf-8',errors='replace'),'exit':p.returncode}
 records.append(record);print(label,'EXIT',p.returncode)
 return p
test=ROOT/'test/modules/effect/test_var64_identity.py'
for label,source in [('BASELINE','variable64.STRESS_BASELINE.c'),('MODIFIED','variable64.STRESS_MODIFIED.c')]:
 cmd(label,[sys.executable,str(test),str(TX/source),str(TX/'stress'/('identity_'+label.lower()+'_confirmed'))])
shutil.copyfile(TX/'variable64.STRESS_MODIFIED.c',TX/'variable64.rollback.stress.c')
assert cmd('ROLLBACK_EXEC',['C:/Program Files/Git/bin/bash.exe',str(TX/'ROLLBACK.sh'),str(TX/'variable64.rollback.stress.c')]).returncode==0
cmd('ROLLBACK',[sys.executable,str(test),str(TX/'variable64.rollback.stress.c'),str(TX/'stress/identity_rollback_confirmed')])
assert records[0]['exit']==1 and records[1]['exit']==0 and records[3]['exit']==1
assert (TX/'variable64.rollback.stress.c').read_bytes()==(TX/'variable64.STRESS_BASELINE.c').read_bytes()
assert cmd('GAME_STRESS_VERIFY',[sys.executable,str(ROOT/'test/modules/effect/stress_variable64.py'),'final','--verify-only']).returncode==0
assert cmd('LEGACY_VERIFY',[sys.executable,str(ROOT/'test/modules/effect/verify_variable64_reproduction.py'),'--dir',str(TX/'stress/legacy'),'--regression-only']).returncode==0
assert cmd('DIFF_CHECK',['git','diff','--check'],cwd=ROOT).returncode==0
shutil.copyfile(TX/'BASELINE.zip',TX/'reconstruct/MODIFIED_FILE.zip')
assert cmd('PATCH_RECONSTRUCT',['git','apply','-p2',str(TX/'DIFF_FILE.patch')],cwd=TX/'reconstruct').returncode==0
assert (TX/'reconstruct/MODIFIED_FILE.zip').read_bytes()==(TX/'MODIFIED_FILE.zip').read_bytes()
shutil.copyfile(TX/'MODIFIED_FILE.zip',TX/'restored.zip')
assert cmd('ROLLBACK_PACKAGE',['C:/Program Files/Git/bin/bash.exe',str(TX/'ROLLBACK.sh'),str(TX/'restored.zip')]).returncode==0
assert (TX/'restored.zip').read_bytes()==(TX/'BASELINE.zip').read_bytes()
for p in ['BASELINE.zip','MODIFIED_FILE.zip','restored.zip']:
 with zipfile.ZipFile(TX/p) as z:assert z.testzip() is None
for p,b in new.items():assert (ROOT/p).read_bytes()==b
baseline=json.loads((TX/'stress/baseline/comparison.json').read_text(encoding='utf-8'))
math=json.loads((TX/'stress/native_math_final/comparison.json').read_text(encoding='utf-8'))
assert math['passed']==10676 and not math['failed']
previous['stress_extension']={'changed_symbols':['Var64_IsStored64','Var64_LookupInScope','Var64_Container','Var64_CalculateRaw','Var64_FindDebt','Var64_NewDebt','Var64_ClearDetour','Var64_ReadNameOnly'],
 'baseline_commit':'0d24c95','baseline_source_sha256':hashlib.sha256((TX/'variable64.STRESS_BASELINE.c').read_bytes()).hexdigest(),
 'modified_source_sha256':hashlib.sha256((TX/'variable64.STRESS_MODIFIED.c').read_bytes()).hexdigest(),
 'commands':records,'baseline_game_summary':{'checks':baseline['checks'],'passed':baseline['passed'],'failed':len(baseline['failed'])},
 'final_game_summary':{'checks':final['checks'],'passed':final['passed'],'failed':len(final['failed'])},
 'raw_math_summary':math,'legacy_checks':48,'legacy_pollution':len(legacy['pollution']),
 'native_identity_coverage':'Actual lookup/identity functions, mocked game container resolver; live resolver separately checked by IDA and runtime probe.',
 'rollback_scope':'Independent source/package copies; live game was not rolled back.',
 'game_command_ledger':str(TX/'stress/final/stress_commands.json'),
 'source_original_unchanged':True,'rollback_source_hash_matches':True,'patch_reconstructs_exact_modified_package':True,
 'errors_retained':['REA cannot open .i64 directly: target_unavailable; used bundled IDA scripts on a copied database.',
 'Default IDA bootstrap failed (missing idalib-mcp / server not ready); explicit installed runtime succeeded.',
 'JSON vtable file first decoded as GBK: UnicodeDecodeError; corrected UTF-8.',
 'Initial attempt to move diagnostic into nonexistent archive directory failed; created directory then moved.',
 'Recursive temporary-database cleanup command blocked before execution; database session later closed without saving. Copy remains.',
 'Raw math first pass: two INT64_MIN with zero cases failed; corrected, final 10676/10676.',
 'Extended game first pass: clear64 observed 4294967296.125 rather than 0; hooked confirmed clear exec, final 516/516.'],
 'remaining':['scoped operands','trigger/temp/arrays','debt persistence','hot-load lifecycle','specialized _64 effect extreme cases','multithread/multiplayer','long-duration/FPS profiling']}
previous['latest_modified_hashes']={p:hashlib.sha256(b).hexdigest() for p,b in new.items()}
(TX/'VERIFICATION.txt').write_text(json.dumps(previous,ensure_ascii=False,indent=2),encoding='utf-8')
roles={}
for n in ['MODIFIED_FILE.zip','DIFF_FILE.patch','VERIFICATION.txt','ROLLBACK.sh']:
 p=TX/n;b=p.read_bytes();roles[n]={'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)};print(json.dumps(roles[n],ensure_ascii=False))
(TX/'artifact_hashes.json').write_text(json.dumps(roles,ensure_ascii=False,indent=2),encoding='utf-8')
(TX/'checkpoint.json').write_text(json.dumps({'ACTIVE_OBJECT':str(ROOT/'src/plugin/SDK_RVA/variable64/variable64.c'),'LAST_CONFIRMED_RESULT':'516/516 stress, 48/48 legacy, 10676/10676 raw math, 8/8 identity, 6/6 string layout; independent rollback reproduces 2/8 baseline','NEXT_EXECUTABLE_ACTION':'Test specialized _64 effect extremes and cross-scope operands; profile readonly classification overhead','INPUT_PATHS':[str(ROOT/'ai_docs/09_脚本数值系统/读档身份与抗压验证.md'),str(TX/'stress/final/comparison.json')],'ACCEPTANCE_EVENT':'Exact oracles and vanilla isolation hold for the newly tested entry paths'},ensure_ascii=False,indent=2),encoding='utf-8')
print('EXTENDED_TRANSACTION_VERIFIED')
