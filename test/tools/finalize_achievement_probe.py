import hashlib,json,pathlib,shutil,subprocess,sys,zipfile
R=pathlib.Path(__file__).resolve().parents[2];T=R/'test/reports/20261012_variable64_transaction';D=R/'test/reports/20261013_achievement_compat'
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def run(c,cwd=R):
 p=subprocess.run(c,cwd=cwd,capture_output=True);return dict(command=c,cwd=str(cwd),stdout=p.stdout.decode('utf-8',errors='replace'),stderr=p.stderr.decode('utf-8',errors='replace'),exit=p.returncode)
build=run(['C:/Program Files/Microsoft Visual Studio/2022/Community/MSBuild/Current/Bin/MSBuild.exe','hoi4plugins.sln','/p:Configuration=Release','/p:Platform=x64','/v:minimal','/nologo']);save(D/'probe_build.json',build);assert build['exit']==0
for phase,code in [('BASELINE',1),('MODIFIED',0),('ROLLBACK',1)]:assert read(D/(phase+'_policy.json'))['result']['exit']==code and read(D/('native_'+phase+'.json'))['exit']==code
assert read(D/'BASELINE_policy.json')['result']['stdout']==read(D/'ROLLBACK_policy.json')['result']['stdout']
assert read(D/'probe_readonly_100.json')['achievement_manager_unchanged']
assert sha(D/'restored.achievement-probe.dll')==sha(D/'hoi4_mod_plugin.BASELINE.dll')
shutil.copyfile(R/'build/Release/hoi4_mod_plugin.dll',D/'hoi4_mod_plugin.PROBE_MODIFIED.dll');assert sha(R.parent/'hoi4_mod_plugin.dll')==sha(D/'hoi4_mod_plugin.PROBE_MODIFIED.dll')
manifest=read(T/'CURRENT_BUILD.json');manifest.update(dll_archive=(D/'hoi4_mod_plugin.PROBE_MODIFIED.dll').relative_to(R).as_posix(),sha256=sha(D/'hoi4_mod_plugin.PROBE_MODIFIED.dll'),reason='Achievement stage1 readonly status command and non-integrated policy foundation; compatibility eligibility hooks and real Steam unlock NOT enabled')
save(T/'CURRENT_BUILD.json',manifest)
with zipfile.ZipFile(D/'PROBE_MODIFIED_SOURCE.zip','w',zipfile.ZIP_DEFLATED) as z:
 for n in ['src/plugin/plugin_main.c','src/plugin/plugin.vcxproj','src/plugin/SDK_RVA/achievement/achievement_probe.c','src/plugin/SDK_RVA/achievement/achievement_policy.h']:z.write(R/n,n)
shutil.copyfile(D/'PROBE_MODIFIED_SOURCE.zip',D/'restored.achievement-probe.source.zip');source_restore=run(['C:/Program Files/Git/bin/bash.exe',str(T/'ROLLBACK.sh'),str(D/'restored.achievement-probe.source.zip')]);assert source_restore['exit']==0 and sha(D/'restored.achievement-probe.source.zip')==sha(D/'PROBE_BASELINE.zip')
with zipfile.ZipFile(T/'MODIFIED_FILE.zip') as z:names=set(z.namelist())
names.update(p.relative_to(R).as_posix() for folder in ['src','ai_docs','test/docs','test/modules/achievement'] for p in (R/folder).rglob('*') if p.is_file() and not any(x in p.parts for x in ['build','__pycache__']))
names.add('test/tools/finalize_achievement_probe.py')
names.update(p.relative_to(R).as_posix() for p in D.iterdir() if p.is_file() and p.name!='checkpoint.json' and p.suffix in ['.json','.txt','.h','.c','.dll','.zip'])
names.discard((D/'checkpoint.json').relative_to(R).as_posix())
with zipfile.ZipFile(T/'MODIFIED_FILE.zip','w',zipfile.ZIP_DEFLATED) as z:
 for n in sorted(names):z.write(R/n,n)
shutil.copyfile(T/'BASELINE.zip',T/'before/MODIFIED_FILE.zip');shutil.copyfile(T/'MODIFIED_FILE.zip',T/'after/MODIFIED_FILE.zip');diff=run(['git','diff','--no-index','--binary','--','before/MODIFIED_FILE.zip','after/MODIFIED_FILE.zip'],T);assert diff['exit']==1;(T/'DIFF_FILE.patch').write_text(diff['stdout'],encoding='utf-8',newline='\n')
shutil.copyfile(T/'BASELINE.zip',T/'reconstruct/MODIFIED_FILE.zip');apply=run(['git','apply','-p2',str(T/'DIFF_FILE.patch')],T/'reconstruct');assert apply['exit']==0 and sha(T/'reconstruct/MODIFIED_FILE.zip')==sha(T/'MODIFIED_FILE.zip')
shutil.copyfile(T/'MODIFIED_FILE.zip',T/'restored.zip');full=run(['C:/Program Files/Git/bin/bash.exe',str(T/'ROLLBACK.sh'),str(T/'restored.zip')]);assert full['exit']==0 and sha(T/'restored.zip')==sha(T/'BASELINE.zip')
audits={}
for key,c in [('docs',[sys.executable,str(R/'test/tools/audit_project_docs.py'),'--package',str(T/'MODIFIED_FILE.zip')]),('console',[sys.executable,str(R/'test/modules/console/audit_external_console_package.py'),str(T/'MODIFIED_FILE.zip')]),('numeric',[sys.executable,str(R/'test/modules/effect/audit_array_api_package.py'),str(T/'MODIFIED_FILE.zip')])]:
 audits[key]=run(c);assert audits[key]['exit']==0,audits[key]
with zipfile.ZipFile(T/'MODIFIED_FILE.zip') as z:
 assert z.testzip() is None
 for n in names:assert z.read(n)==(R/n).read_bytes(),n
v=read(T/'VERIFICATION.txt');v['achievement_probe_stage1']=dict(stage='readonly probe and policy foundation, NOT achievement unlock implementation',build=build,policy_model={p:read(D/(p+'_policy.json')) for p in ['BASELINE','MODIFIED','ROLLBACK']},native_probe={p:read(D/('native_'+p+'.json')) for p in ['BASELINE','MODIFIED','ROLLBACK','FINAL']},readonly_100=read(D/'probe_readonly_100.json'),source_restore=source_restore,source_restored_sha256=sha(D/'restored.achievement-probe.source.zip'),dll_restored_sha256=sha(D/'restored.achievement-probe.dll'),patch_reconstruction=apply,full_restore=full,audits=audits,compatibility_hooks_enabled=False,steam_unlock_verified=False,steam_mutator_calls_in_probe=False)
v['latest_modified_hashes']={n:sha(R/n) for n in names};save(T/'VERIFICATION.txt',v)
c=read(T/'checkpoint.json');c.update(ACTIVE_OBJECT=str(R/'src/plugin/SDK_RVA/achievement/achievement_probe.c'),LAST_CONFIRMED_RESULT='Stage1 observer deployed: baseline/rollback Unknown command exit1, modified readonly success exit0; policy reference509/512 ->512/512 ->509/512;100 native reads preserve168 manager bytes. Active mod overrides vanilla achievements with empty file, definitions0. Compatibility hooks and Steam unlock NOT enabled.',NEXT_EXECUTABLE_ACTION='Implement/test definition-source fallback for empty active override without editing mod file; then scoped eligibility/possible context and old-save reconstruction, preserve happened and native real-submit path. Do not set manager+A3 debug flag or bypass mod storage checksum.',INPUT_PATHS=[str(R/'ai_docs/11_成就系统/资格链路与阶段进展.md'),str(D/'native_FINAL.json'),str(D/'checksum_function_strings.json'),str(D/'0x1406202c0.txt'),str(D/'0x140621040.txt')],ACCEPTANCE_EVENT='Native qualified candidate initialization and actual happened checks with isolated submission tests, then targeted real Steam callback verification; full feature still unfinished',current_build=manifest,achievement_probe_implemented=True,achievement_compatibility_enabled=False)
save(T/'checkpoint.json',c);save(D/'checkpoint.json',c)
roles={}
for n in ['MODIFIED_FILE.zip','DIFF_FILE.patch','VERIFICATION.txt','ROLLBACK.sh']:
 p=T/n;b=p.read_bytes();roles[n]=dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest());print(json.dumps(roles[n],ensure_ascii=False))
save(T/'artifact_hashes.json',roles);print('ACHIEVEMENT_STAGE1_VERIFIED; FULL_UNLOCK_FEATURE_UNFINISHED')
