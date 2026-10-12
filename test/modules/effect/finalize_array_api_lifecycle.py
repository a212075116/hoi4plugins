import hashlib,json,pathlib,shutil,subprocess,sys,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[3];TX=ROOT/'test/reports/20261012_variable64_transaction';A=TX/'api'
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
phase=sys.argv[1];out=A/phase;result=read(out/'comparison.json');assert result['exit']==0 and result['checks']==result['passed'] and result['alive']
assert sha(ROOT.parent/'hoi4_mod_plugin.dll')==result['dll_sha256']==sha(A/'hoi4_mod_plugin.MODIFIED.dll')
assert sha(ROOT/'src/plugin/SDK_RVA/variable64/variable64.c')=='ec54864342e9e8811aaea73eb7ef66ed5f4f9328a7083854120f190880755c1e'
old=read(TX/'VERIFICATION.txt')
for path,expected in old['latest_modified_hashes'].items():
 if path.startswith('src/'):assert sha(ROOT/path)==expected,path
with zipfile.ZipFile(TX/'MODIFIED_FILE.zip') as z:paths=set(z.namelist())
paths.update(['test/modules/effect/verify_array64_api_lifecycle.py','test/modules/effect/finalize_array_api_lifecycle.py',
 'ai_docs/09_脚本数值系统/Array64事务归属与旧存档验收.md','ai_docs/09_脚本数值系统/Array64单人交付说明.md'])
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
old['array_api_lifecycle_extension']={'symbol':'recover_array64; __v64t_prf_n0/p; __v64o_prf_b0/i0; __v64sys_id2',
 'runtime':result,'inputs':read(out/'records.json'),'expected':read(out/'expected.json'),'sidecar_hashes':read(out/'sidecars.json'),
 'literal_commands':{label:read(out/(label+'_commands.json')) for label in ['matrix','foreign_scope','persist','restart_bad','latest','old_save_new_sidecar','paired_old']},
 'ui_access':read(out/'ui_access.json'),'production_source_changed':False,'production_dll_sha256':result['dll_sha256'],'package_three_state':audit,
 'patch_reconstructs_exact_package':True,'package_rollback_exact':True,
 'original_save_hashes':{label:sha(out/(label+'_save.hoi4')) for label in ['persist','restart_bad']},
 'limits':['No forced process crash/power loss','Only latest sidecar retained; historical pairing requires explicit paired backup','Native UI surface unavailable; hover and localized result-word visual acceptance not performed','Bounded singleplayer tests only; no multiplayer/long soak/atomic save-sidecar claim']}
old['latest_modified_hashes']={n:sha(ROOT/n) for n in sorted(paths)}
(TX/'VERIFICATION.txt').write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8')
roles={}
for n in ['MODIFIED_FILE.zip','DIFF_FILE.patch','VERIFICATION.txt','ROLLBACK.sh']:
 p=TX/n;b=p.read_bytes();roles[n]={'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)};print(json.dumps(roles[n],ensure_ascii=False))
(TX/'artifact_hashes.json').write_text(json.dumps(roles,ensure_ascii=False,indent=2),encoding='utf-8')
(TX/'checkpoint.json').write_text(json.dumps({'ACTIVE_OBJECT':str(ROOT/'src/plugin/SDK_RVA/variable64/variable64.c'),
 'LAST_CONFIRMED_RESULT':f'Public receipt/ownership/native identity rejection, five same-name foreign scope journals, saved bad nonce/branch restart recovery, old-save/new-intent rejection and exact old pair acceptance {result["passed"]}/{result["checks"]}; production DLL unchanged; bounded singleplayer handoff documented; native UI unavailable.',
 'NEXT_EXECUTABLE_ACTION':'Run remaining singleplayer crash/soak release acceptance with existing public APIs and exact paired backups; retain the visual gate until native UI access is enabled; do not add features or claim multiplayer acceptance.',
 'INPUT_PATHS':[str(ROOT/'ai_docs/09_脚本数值系统/Array64单人交付说明.md'),str(out/'comparison.json')],
 'ACCEPTANCE_EVENT':'Bounded singleplayer implementation and public lifecycle evidence delivered, residual release checks explicitly separated'},ensure_ascii=False,indent=2),encoding='utf-8')
print('LIFECYCLE_PACKAGE_VERIFIED')
