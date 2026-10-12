import hashlib,json,pathlib,shutil,subprocess,sys,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[2];TX=ROOT/'test/reports/20261012_variable64_transaction';D=TX/'external_console'
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def capture(command,cwd=None):
 p=subprocess.run(command,cwd=cwd,capture_output=True)
 return {'command':command,'cwd':str(cwd) if cwd else str(ROOT),'stdout':p.stdout.decode('utf-8',errors='replace'),'stderr':p.stderr.decode('utf-8',errors='replace'),'exit':p.returncode}
def pack(path,names):
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
  for name in sorted(names):
   i=zipfile.ZipInfo(name,(2026,10,13,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;z.writestr(i,(ROOT/name).read_bytes())
old=read(TX/'VERIFICATION.txt')
assert sha(D/'SOURCE_BASELINE.zip')=='b3a5efd29767fd53c98935a73317ce281547d3d17aa20a8d7a128b0c1ca1c274'
assert sha(D/'POLICY_AUDIT_BASELINE.py')=='6466e048e898100d006ff03a1a5820dbae5a2b0360c4c4f0235ec5a3b1521be6'
assert sha(D/'hoi4_mod_plugin.BASELINE.dll')=='959aab27d536af1a302f3a3db8575e660eae41b87f5209a0d07f135bb1143e5f'
for filename in ['hoi4_mod_plugin.dll','hoi4_debug_console.exe']:
 p=pathlib.Path(filename);assert sha(ROOT.parent/filename)==sha(D/(p.stem+'.MODIFIED'+p.suffix))==sha(ROOT/'build/Release'/filename)
manifest={'dll_archive':(D/'hoi4_mod_plugin.MODIFIED.dll').relative_to(ROOT).as_posix(),'sha256':sha(D/'hoi4_mod_plugin.MODIFIED.dll'),'helper_archive':(D/'hoi4_debug_console.MODIFIED.exe').relative_to(ROOT).as_posix(),'helper_sha256':sha(D/'hoi4_debug_console.MODIFIED.exe'),'reason':'External local console, native permission dispatch, FIFO cancellation, bounded incremental logs and obsolete camera animation cancellation'}
(TX/'CURRENT_BUILD.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
for n,passed in [('modified_ready_final',29),('menu_final',2),('lifecycle_final',6),('endpoint_collision',3),('stream',4)]:
 r=read(D/(n+'.json'));assert r['exit']==0 and r['passed']==r['checks']==passed,n
for n,passed,code in [('baseline_native',0,1),('modified_native',3,0),('rollback_native',0,1)]:
 r=read(D/(n+'_camera_race.json'));assert r['commands_success'] and r['passed']==passed and r['exit']==code,n
for name in ['baseline_reopened','rollback']:
 assert read(D/(name+'.json'))['records'][0]['exit']==2
runtime=read(D/'modified_ready_final.json');tids=next(r['details']['tids'] for r in runtime['rows'] if r['name']=='game-thread-only')
window=read(D/'READY_WINDOW_THREAD.json');assert runtime['pid']==window['pid'] and all(t in [r['thread'] for r in window['windows'] if r['visible']] for t in tids)
assert read(D/'tail_self_test.json')['exit']==0 and '14/14' in read(D/'tail_self_test.json')['stdout']
assert read(TX/'camera_unify/external_console_regression/comparison.json')['passed']==9
docs={p.relative_to(ROOT).as_posix() for parent in ['ai_docs','test/docs'] for p in (ROOT/parent).rglob('*.md')}
files={p.relative_to(ROOT).as_posix() for p in (ROOT/'src').rglob('*') if p.is_file() and not any(x in p.parts for x in ['build','.vs','__pycache__'])}
files.update(docs);files.update(['hoi4plugins.sln','test/tools/hoi4_launch.py','test/tools/audit_user_todo_policy.py','test/tools/finalize_external_console.py'])
files.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'test/modules/console').glob('*external_console*.py'))
files.add('test/modules/console/verify_camera_command_race.py')
files.update([manifest['dll_archive'],manifest['helper_archive'],'test/reports/20261012_variable64_transaction/CURRENT_BUILD.json'])
pack(D/'SOURCE_MODIFIED.zip',files)
shutil.copyfile(D/'SOURCE_MODIFIED.zip',D/'restored.external-console.source.zip')
restore=capture(['C:/Program Files/Git/bin/bash.exe',str(TX/'ROLLBACK.sh'),str(D/'restored.external-console.source.zip')]);assert restore['exit']==0 and sha(D/'restored.external-console.source.zip')==sha(D/'SOURCE_BASELINE.zip')
source_three={}
for label,file in [('BASELINE','SOURCE_BASELINE.zip'),('MODIFIED','SOURCE_MODIFIED.zip'),('ROLLBACK','restored.external-console.source.zip')]:
 r=capture([sys.executable,str(ROOT/'test/modules/console/audit_external_console_package.py'),str(D/file)]);r['result']=json.loads(r['stdout']);source_three[label]=r;print(label,r['result']['passed'],'/',r['result']['checks'],'exit',r['exit'])
assert source_three['MODIFIED']['exit']==0 and source_three['BASELINE']['exit']==source_three['ROLLBACK']['exit']==1
assert source_three['BASELINE']['result']['rows']==source_three['ROLLBACK']['result']['rows']
shutil.copyfile(ROOT/'test/tools/audit_user_todo_policy.py',D/'restored.external-console.policy.py')
policy_restore=capture(['C:/Program Files/Git/bin/bash.exe',str(TX/'ROLLBACK.sh'),str(D/'restored.external-console.policy.py')]);assert policy_restore['exit']==0 and sha(D/'restored.external-console.policy.py')==sha(D/'POLICY_AUDIT_BASELINE.py')
with zipfile.ZipFile(TX/'MODIFIED_FILE.zip') as z:names=set(z.namelist())
names.update(files);names.update((D/n).relative_to(ROOT).as_posix() for n in ['SOURCE_BASELINE.zip','POLICY_AUDIT_BASELINE.py','hoi4_mod_plugin.BASELINE.dll'])
names.update(p.relative_to(ROOT).as_posix() for p in D.glob('*.json'))
names.update((D/n).relative_to(ROOT).as_posix() for n in ['hoi4_mod_plugin.DISPATCH_DIRECT.dll','hoi4_mod_plugin.ENTRY_ONLY.dll','SOURCE_DISPATCH_DIRECT.zip'])
pack(TX/'MODIFIED_FILE.zip',names)
shutil.copyfile(TX/'BASELINE.zip',TX/'before/MODIFIED_FILE.zip');shutil.copyfile(TX/'MODIFIED_FILE.zip',TX/'after/MODIFIED_FILE.zip')
patch=capture(['git','diff','--no-index','--binary','--','before/MODIFIED_FILE.zip','after/MODIFIED_FILE.zip'],TX);assert patch['exit']==1
(TX/'DIFF_FILE.patch').write_text(patch['stdout'],encoding='utf-8',newline='\n')
shutil.copyfile(TX/'BASELINE.zip',TX/'reconstruct/MODIFIED_FILE.zip')
apply=capture(['git','apply','-p2',str(TX/'DIFF_FILE.patch')],TX/'reconstruct');assert apply['exit']==0 and sha(TX/'reconstruct/MODIFIED_FILE.zip')==sha(TX/'MODIFIED_FILE.zip')
shutil.copyfile(TX/'MODIFIED_FILE.zip',TX/'restored.zip')
full_restore=capture(['C:/Program Files/Git/bin/bash.exe',str(TX/'ROLLBACK.sh'),str(TX/'restored.zip')]);assert full_restore['exit']==0 and sha(TX/'restored.zip')==sha(TX/'BASELINE.zip')
audit=capture([sys.executable,str(ROOT/'test/modules/console/audit_external_console_package.py'),str(TX/'MODIFIED_FILE.zip')]);assert audit['exit']==0
numeric=capture([sys.executable,str(ROOT/'test/modules/effect/audit_array_api_package.py'),str(TX/'MODIFIED_FILE.zip')]);assert numeric['exit']==0
policy=capture([sys.executable,str(ROOT/'test/tools/audit_user_todo_policy.py'),str(TX/'MODIFIED_FILE.zip')]);assert policy['exit']==0
docs_audit=capture([sys.executable,str(ROOT/'test/tools/audit_project_docs.py'),'--package',str(TX/'MODIFIED_FILE.zip')]);assert docs_audit['exit']==0
with zipfile.ZipFile(TX/'MODIFIED_FILE.zip') as z:
 assert z.testzip() is None
 for n in z.namelist():assert z.read(n)==(ROOT/n).read_bytes(),n
old['external_console_extension']={'implemented':True,'current_build':manifest,'source_three_state':source_three,'source_restore':restore,'source_restore_exact':True,'native_rollback':read(D/'native_rollback.json'),'native_three_state':{'BASELINE':read(D/'BASELINE_COMMAND.json'),'MODIFIED':runtime['records'][0],'ROLLBACK':read(D/'rollback.json')['records'][0]},'camera_three_state':{label:read(D/(n+'_camera_race.json')) for label,n in [('BASELINE','baseline_native'),('MODIFIED','modified_native'),('ROLLBACK','rollback_native')]},'runtime':runtime,'menu':read(D/'menu_final.json'),'lifecycle':read(D/'lifecycle_final.json'),'endpoint_collision':read(D/'endpoint_collision.json'),'stream':read(D/'stream.json'),'tail_self_test':read(D/'tail_self_test.json'),'window_thread':window,'camera_regression':read(TX/'camera_unify/external_console_regression/comparison.json'),'build':read(D/'build_ready_final.json'),'final_ready':read(D/'FINAL_READY.json'),'audits':{'external_package':audit,'numeric_package':numeric,'user_policy':policy,'docs':docs_audit},'reconstruction':apply,'patch_diff_command':patch['command'],'patch_diff_exit':patch['exit'],'patch_exact':True,'full_restore':full_restore,'full_restore_exact':True,'policy_restore':policy_restore,'source_baseline_sha256':sha(D/'SOURCE_BASELINE.zip'),'notes':['Full original transaction baseline is retained; latest per-operation source/DLL/policy baselines extend its roles.','Menus/loading lack execution context and cancel; not unrestricted command availability.','Permission predicates injected; no real multiplayer/Ironman campaign test.','Native exception/remote clients/multi-hour soak/visual wide-character edit are not certified.','Initial macro/header/StartService compile error exit1 corrected.','Initial readiness, short predicate Frida hook, native alias diagnostic, camera race and collision fixture failed records are preserved.','A docs write failed due implicit GBK read; corrected to explicit UTF-8.']}
old['latest_modified_hashes']={n:sha(ROOT/n) for n in names};(TX/'VERIFICATION.txt').write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8')
checkpoint=read(TX/'checkpoint.json');checkpoint.update({'ACTIVE_OBJECT':str(ROOT/'src/plugin/SDK_RVA/console/debug_console.c'),'LAST_CONFIRMED_RESULT':'External console implemented; runtime29/29 with240 concurrent successes; tail14/14; lifecycle6/6; menu2/2; endpoint3/3; stream4/4. Native camera race BASELINE0/3 MODIFIED3/3 ROLLBACK0/3 and prior shared-path9/9. Source/archive/DLL rollback hashes exact; modified production restored.','NEXT_EXECUTABLE_ACTION':'User-only U04 console display/edit experience and existing U01/U02/U03 checks; no automatic widening into multiplayer, power loss or multi-hour soak.','INPUT_PATHS':[str(ROOT/'test/docs/external_console.md'),str(ROOT/'test/docs/用户尚未测试的待办事项.md'),str(D/'modified_final.json')],'ACCEPTANCE_EVENT':'Built and deployed independent console, observed native game-thread results and bounded rejection/cancellation, completed exact reconstruction/rollback and restored MODIFIED production','external_console_implemented':True,'current_build':manifest});checkpoint['user_acceptance_policy']['external_console']='v1 built/deployed/verified; U04 subjective GUI input experience remains';(TX/'checkpoint.json').write_text(json.dumps(checkpoint,ensure_ascii=False,indent=2),encoding='utf-8')
roles={}
for name in ['MODIFIED_FILE.zip','DIFF_FILE.patch','VERIFICATION.txt','ROLLBACK.sh']:
 p=TX/name;b=p.read_bytes();roles[name]={'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)};print(json.dumps(roles[name],ensure_ascii=False))
(TX/'artifact_hashes.json').write_text(json.dumps(roles,ensure_ascii=False,indent=2),encoding='utf-8');print('EXTERNAL_CONSOLE_TRANSACTION_VERIFIED')
