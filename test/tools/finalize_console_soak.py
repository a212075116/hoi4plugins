import hashlib,json,pathlib,shutil,subprocess,sys,zipfile
R=pathlib.Path(__file__).resolve().parents[2];T=R/'test/reports/20261012_variable64_transaction';D=T/'console_stress'
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def run(c,cwd=None):
 p=subprocess.run(c,cwd=cwd,capture_output=True);return {'command':c,'cwd':str(cwd or R),'stdout':p.stdout.decode('utf-8',errors='replace'),'stderr':p.stderr.decode('utf-8',errors='replace'),'exit':p.returncode}
def pack(p,names):
 with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:
  for n in sorted(names):
   i=zipfile.ZipInfo(n,(2026,10,13,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;z.writestr(i,(R/n).read_bytes())
old=read(T/'VERIFICATION.txt');soak=read(D/'soak_result.json');assert soak.get('completed_seconds',0)>=2700
for n in ['hoi4_mod_plugin.dll','hoi4_debug_console.exe']:
 p=pathlib.Path(n);assert sha(R.parent/n)==sha(R/'build/Release'/n);shutil.copyfile(R.parent/n,D/(p.stem+'.MODIFIED'+p.suffix))
manifest={'dll_archive':(D/'hoi4_mod_plugin.MODIFIED.dll').relative_to(R).as_posix(),'sha256':sha(D/'hoi4_mod_plugin.MODIFIED.dll'),'helper_archive':(D/'hoi4_debug_console.MODIFIED.exe').relative_to(R).as_posix(),'helper_sha256':sha(D/'hoi4_debug_console.MODIFIED.exe'),'reason':'Lossless bounded log consumption, asynchronous bounded input worker, reserved interactive pipe; 2700-second observed single-player run, limitations stated separately'}
(T/'CURRENT_BUILD.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
files={p.relative_to(R).as_posix() for folder in ['src','ai_docs','test/docs','test/modules/console'] for p in (R/folder).rglob('*') if p.is_file() and not any(x in p.parts for x in ['build','__pycache__'])}
files.update(['hoi4plugins.sln','test/tools/finalize_console_soak.py','test/tools/hoi4_launch.py','test/modules/console/audit_external_console_package.py',manifest['dll_archive'],manifest['helper_archive'],'test/reports/20261012_variable64_transaction/CURRENT_BUILD.json'])
pack(D/'MODIFIED_SOURCE.zip',files);shutil.copyfile(D/'MODIFIED_SOURCE.zip',D/'restored.console-soak.source.zip')
restore=run(['C:/Program Files/Git/bin/bash.exe',str(T/'ROLLBACK.sh'),str(D/'restored.console-soak.source.zip')]);assert restore['exit']==0 and sha(D/'restored.console-soak.source.zip')==sha(D/'BASELINE.zip')
binary_restore={}
for n in ['hoi4_mod_plugin.dll','hoi4_debug_console.exe']:
 p=pathlib.Path(n);copy=D/('restored.console-soak'+p.suffix);shutil.copyfile(D/(p.stem+'.MODIFIED'+p.suffix),copy)
 result=run(['C:/Program Files/Git/bin/bash.exe',str(T/'ROLLBACK.sh'),str(copy)]);assert result['exit']==0 and sha(copy)==sha(D/(p.stem+'.BASELINE'+p.suffix));binary_restore[n]=dict(result,restored_sha256=sha(copy))
selftest=run([str(R/'build/Release/hoi4_debug_console.exe'),'--self-test']);assert selftest['exit']==0 and '17/17' in selftest['stdout']
with zipfile.ZipFile(T/'MODIFIED_FILE.zip') as z:names=set(z.namelist())
names.update(files)
for n in ['BASELINE.zip','hoi4_mod_plugin.BASELINE.dll','hoi4_debug_console.BASELINE.exe','tail_three_state.json','baseline.json','build.json','soak_result.json','fixture.events.txt','samples.jsonl','progress.json']:
 names.add((D/n).relative_to(R).as_posix())
pack(T/'MODIFIED_FILE.zip',names)
shutil.copyfile(T/'BASELINE.zip',T/'before/MODIFIED_FILE.zip');shutil.copyfile(T/'MODIFIED_FILE.zip',T/'after/MODIFIED_FILE.zip')
p=run(['git','diff','--no-index','--binary','--','before/MODIFIED_FILE.zip','after/MODIFIED_FILE.zip'],T);assert p['exit']==1
(T/'DIFF_FILE.patch').write_text(p['stdout'],encoding='utf-8',newline='\n')
shutil.copyfile(T/'BASELINE.zip',T/'reconstruct/MODIFIED_FILE.zip');apply=run(['git','apply','-p2',str(T/'DIFF_FILE.patch')],T/'reconstruct');assert apply['exit']==0 and sha(T/'reconstruct/MODIFIED_FILE.zip')==sha(T/'MODIFIED_FILE.zip')
shutil.copyfile(T/'MODIFIED_FILE.zip',T/'restored.zip');full=run(['C:/Program Files/Git/bin/bash.exe',str(T/'ROLLBACK.sh'),str(T/'restored.zip')]);assert full['exit']==0 and sha(T/'restored.zip')==sha(T/'BASELINE.zip')
audits={}
for key,c in [('package',[sys.executable,str(R/'test/modules/console/audit_external_console_package.py'),str(T/'MODIFIED_FILE.zip')]),('numeric',[sys.executable,str(R/'test/modules/effect/audit_array_api_package.py'),str(T/'MODIFIED_FILE.zip')]),('docs',[sys.executable,str(R/'test/tools/audit_project_docs.py'),'--package',str(T/'MODIFIED_FILE.zip')])]:
 result=run(c);assert result['exit']==0,(key,result);audits[key]=result
with zipfile.ZipFile(T/'MODIFIED_FILE.zip') as z:
 assert z.testzip() is None
 for n in names:assert z.read(n)==(R/n).read_bytes(),n
old['console_soak_extension']={'contract_confirmed':True,'observed_soak':soak,'tail_three_state':read(D/'tail_three_state.json'),'build':read(D/'build.json'),'self_test':selftest,'baseline':read(D/'baseline.json'),'binary_restore':binary_restore,'source_restore':restore,'source_restore_exact':True,'patch_reconstruction':apply,'full_restore':full,'full_restore_exact':True,'audits':audits,'current_build':manifest,'actual_gui_visual_tested':False,'actual_multiplayer_tested':False,'native_gpu_present_measured':False,'multiplayer_requirement':'reuse verified native multiplayer detection; real multiplayer verification deferred and not certified','historical_bridge_three_state':old['external_console_extension']['native_three_state']}
old['latest_modified_hashes']={n:sha(R/n) for n in names};(T/'VERIFICATION.txt').write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8')
c=read(T/'checkpoint.json');c.update({'ACTIVE_OBJECT':str(R/'src/debug_console/main.cpp'),'LAST_CONFIRMED_RESULT':f"Console persistent shared-core soak {soak.get('completed_seconds')} seconds, exit={soak['exit']}; lossless log/async input/reserved lane protections implemented. Explicit metrics and untested GUI/GPU/multiplayer boundaries retained.",'NEXT_EXECUTABLE_ACTION':'Review any measured performance/resource failures; multiplayer instruction-disable verification deferred until appropriate environment; user GUI U04 remains. Do not claim real multiplayer or GPU Present passed.','INPUT_PATHS':[str(D/'soak_result.json'),str(R/'test/docs/console_stress.md')],'current_build':manifest});(T/'checkpoint.json').write_text(json.dumps(c,ensure_ascii=False,indent=2),encoding='utf-8')
roles={}
for n in ['MODIFIED_FILE.zip','DIFF_FILE.patch','VERIFICATION.txt','ROLLBACK.sh']:
 p=T/n;b=p.read_bytes();roles[n]={'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()};print(json.dumps(roles[n],ensure_ascii=False))
(T/'artifact_hashes.json').write_text(json.dumps(roles,ensure_ascii=False,indent=2),encoding='utf-8');print('SOAK_TRANSACTION_VERIFIED')
