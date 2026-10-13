import hashlib,json,pathlib,shutil,subprocess,sys,zipfile
R=pathlib.Path(__file__).resolve().parents[2];T=R/'test/reports/20261012_variable64_transaction';D=T/'console_permission'
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def run(c,cwd=R):
 p=subprocess.run(c,cwd=cwd,capture_output=True);return dict(command=c,cwd=str(cwd),stdout=p.stdout.decode('utf-8',errors='replace'),stderr=p.stderr.decode('utf-8',errors='replace'),exit=p.returncode)
build=run(['C:/Program Files/Microsoft Visual Studio/2022/Community/MSBuild/Current/Bin/MSBuild.exe','hoi4plugins.sln','/p:Configuration=Release','/p:Platform=x64','/v:minimal','/nologo']);save(D/'build.json',build);assert build['exit']==0
selftest=run([str(R/'build/Release/hoi4_debug_console.exe'),'--self-test']);assert selftest['exit']==0
assert read(D/'MODIFIED.json')['result']['exit']==0
assert read(D/'BASELINE.json')['result']['exit']==read(D/'ROLLBACK.json')['result']['exit']==1
assert read(D/'BASELINE.json')['result']['stdout']==read(D/'ROLLBACK.json')['result']['stdout']
assert sha(D/'restored.console-permission.c')==sha(D/'debug_console.BASELINE.c')
shutil.copyfile(R/'src/plugin/SDK_RVA/console/debug_console.c',D/'debug_console.MODIFIED.c');shutil.copyfile(R/'build/Release/hoi4_mod_plugin.dll',D/'hoi4_mod_plugin.MODIFIED.dll')
shutil.copyfile(D/'hoi4_mod_plugin.MODIFIED.dll',D/'restored.console-permission.dll')
restore=run(['C:/Program Files/Git/bin/bash.exe',str(T/'ROLLBACK.sh'),str(D/'restored.console-permission.dll')]);assert restore['exit']==0 and sha(D/'restored.console-permission.dll')==sha(D/'hoi4_mod_plugin.BASELINE.dll')
manifest=read(T/'CURRENT_BUILD.json');manifest.update(dll_archive=(D/'hoi4_mod_plugin.MODIFIED.dll').relative_to(R).as_posix(),sha256=sha(D/'hoi4_mod_plugin.MODIFIED.dll'),reason='External-only single-player Ironman/developer dispatch allowed; multiplayer independently refused; 16-case matrix plus UI/exception restore, real no-debug Ironman6/6, 100+100 readonly requests and 60s survival verified; actual multiplayer remains pending')
assert sha(R.parent/'hoi4_mod_plugin.dll')==manifest['sha256'];save(T/'CURRENT_BUILD.json',manifest)
with zipfile.ZipFile(T/'MODIFIED_FILE.zip') as z:names=set(z.namelist())
names.update(p.relative_to(R).as_posix() for folder in ['src','ai_docs','test/docs','test/modules/console'] for p in (R/folder).rglob('*') if p.is_file() and not any(v in p.parts for v in ['build','__pycache__']))
names.update(['test/tools/finalize_console_permission.py','test/tools/launch_console_permission_session.py','test/tools/launch_detached_console_session.py']);names.update(p.relative_to(R).as_posix() for p in D.iterdir() if p.is_file() and p.suffix in ['.json','.c','.cpp','.dll','.exe'])
with zipfile.ZipFile(T/'MODIFIED_FILE.zip','w',zipfile.ZIP_DEFLATED) as z:
 for n in sorted(names):z.write(R/n,n)
shutil.copyfile(T/'BASELINE.zip',T/'before/MODIFIED_FILE.zip');shutil.copyfile(T/'MODIFIED_FILE.zip',T/'after/MODIFIED_FILE.zip')
diff=run(['git','diff','--no-index','--binary','--','before/MODIFIED_FILE.zip','after/MODIFIED_FILE.zip'],T);assert diff['exit']==1;(T/'DIFF_FILE.patch').write_text(diff['stdout'],encoding='utf-8',newline='\n')
shutil.copyfile(T/'BASELINE.zip',T/'reconstruct/MODIFIED_FILE.zip');apply=run(['git','apply','-p2',str(T/'DIFF_FILE.patch')],T/'reconstruct');assert apply['exit']==0 and sha(T/'reconstruct/MODIFIED_FILE.zip')==sha(T/'MODIFIED_FILE.zip')
shutil.copyfile(T/'MODIFIED_FILE.zip',T/'restored.zip');full=run(['C:/Program Files/Git/bin/bash.exe',str(T/'ROLLBACK.sh'),str(T/'restored.zip')]);assert full['exit']==0 and sha(T/'restored.zip')==sha(T/'BASELINE.zip')
audits={}
for k,c in [('package',[sys.executable,str(R/'test/modules/console/audit_external_console_package.py'),str(T/'MODIFIED_FILE.zip')]),('numeric',[sys.executable,str(R/'test/modules/effect/audit_array_api_package.py'),str(T/'MODIFIED_FILE.zip')]),('docs',[sys.executable,str(R/'test/tools/audit_project_docs.py'),'--package',str(T/'MODIFIED_FILE.zip')])]:
 audits[k]=run(c);assert audits[k]['exit']==0,audits[k]
with zipfile.ZipFile(T/'MODIFIED_FILE.zip') as z:
 assert z.testzip() is None
 for n in names:assert z.read(n)==(R/n).read_bytes(),n
v=read(T/'VERIFICATION.txt');v['console_permission_extension']=dict(target=str(R/'src/plugin/SDK_RVA/console/debug_console.c'),changed_branch='Execute -> DispatchExternal network precheck and scoped developer selector with finally-restored native UI state',three_state={p:read(D/(p+'.json')) for p in ['BASELINE','MODIFIED','ROLLBACK']},build=build,selftest=selftest,source_restored_sha256=sha(D/'restored.console-permission.c'),binary_restore=restore,binary_restored_sha256=sha(D/'restored.console-permission.dll'),patch_reconstruction=apply,full_restore=full,audits=audits,game_launch=read(D/'detached_launch.json'),native_attempt=read(D/'native.json'),native_verified=read(D/'native.json')['exit']==0,actual_multiplayer=False,actual_ironman_save=read(D/'native.json')['actual_ironman_save'],production_readonly=read(D/'production_ui_preserved_100.json'),post_native_readonly=read(D/'post_native_100.json'),final_health=read(D/'final_health.json'),crash_contexts=read(D/'crash_contexts.json'),prior_unavailable_context=read(D/'native_unavailable_context.json'),baseline_health=read(D/'baseline_session_health.json'),save_backup=read(D/'save_backup.json'),save_final=read(D/'save_final.json'),production_sha256=manifest['sha256'])
v['latest_modified_hashes']={n:sha(R/n) for n in names};save(T/'VERIFICATION.txt',v)
c=read(T/'checkpoint.json');c.update(ACTIVE_OBJECT=str(R/'src/plugin/SDK_RVA/console/debug_console.c'),LAST_CONFIRMED_RESULT='Implemented/deployed external-only SP Ironman/developer policy and native UI-state preservation. Matrix5/16->16/16->5/16; exception/UI restore passed; native no-debug real Ironman6/6; readonly100+100 and 60s survival; saves7/7 unchanged. True multiplayer not tested.',NEXT_EXECUTABLE_ACTION='User feedback on external-console interactions; future coordinated real multiplayer verification remains deferred. Do not repeat completed tests or claim dangerous developer commands individually validated.',INPUT_PATHS=[str(D/'native.json'),str(R/'test/modules/console/verify_console_permissions_native.py'),str(R/'test/docs/console_permission.md')],ACCEPTANCE_EVENT='Observed native no-debug developer dispatch in real Ironman, network injection rejects before handler, scoped/UI state restored, readonly survival and exact rollback/reconstruction verified',current_build=manifest);save(T/'checkpoint.json',c)
roles={}
for n in ['MODIFIED_FILE.zip','DIFF_FILE.patch','VERIFICATION.txt','ROLLBACK.sh']:
 p=T/n;b=p.read_bytes();roles[n]=dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest());print(json.dumps(roles[n],ensure_ascii=False))
save(T/'artifact_hashes.json',roles);print('PERMISSION_TRANSACTION_VERIFIED; NATIVE6_6; READONLY100_100; SAVE7_7')
