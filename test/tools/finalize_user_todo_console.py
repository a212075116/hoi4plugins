import hashlib,json,pathlib,shutil,subprocess,sys,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[2];TX=ROOT/'test/reports/20261012_variable64_transaction';D=TX/'user_todo_console'
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
old=read(TX/'VERIFICATION.txt')
for n,h in old['latest_modified_hashes'].items():
 if n.startswith('src/'):assert sha(ROOT/n)==h,n
assert sha(ROOT.parent/'hoi4_mod_plugin.dll')==read(TX/'CURRENT_BUILD.json')['sha256']
docs=[p.relative_to(ROOT).as_posix() for root in ['ai_docs','test/docs'] for p in (ROOT/root).rglob('*.md')]
def pack(path,names):
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
  for n in sorted(names):
   i=zipfile.ZipInfo(n,(2026,10,12,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;z.writestr(i,(ROOT/n).read_bytes())
pack(D/'DOCS_MODIFIED.zip',docs);shutil.copyfile(D/'DOCS_MODIFIED.zip',D/'restored.user-policy.docs.zip')
p=subprocess.run(['C:/Program Files/Git/bin/bash.exe',str(TX/'ROLLBACK.sh'),str(D/'restored.user-policy.docs.zip')],capture_output=True);assert p.returncode==0 and sha(D/'restored.user-policy.docs.zip')==sha(D/'DOCS_BASELINE.zip')
audit={}
for label,path in [('baseline',D/'DOCS_BASELINE.zip'),('modified',D/'DOCS_MODIFIED.zip'),('rollback',D/'restored.user-policy.docs.zip')]:
 command=[sys.executable,str(ROOT/'test/tools/audit_user_todo_policy.py'),str(path)];p=subprocess.run(command,capture_output=True);audit[label]={'command':command,'stdout':p.stdout.decode('utf-8'),'stderr':p.stderr.decode('utf-8'),'exit':p.returncode,'result':json.loads(p.stdout)};print(label,p.returncode,audit[label]['result']['passed'],'/',audit[label]['result']['checks'])
assert audit['modified']['exit']==0 and audit['baseline']['exit']==audit['rollback']['exit']==1
assert audit['baseline']['result']['rows']==audit['rollback']['result']['rows']
with zipfile.ZipFile(TX/'MODIFIED_FILE.zip') as z:paths=set(z.namelist())
paths.update(docs);paths.update(['test/tools/audit_user_todo_policy.py','test/tools/finalize_user_todo_console.py','test/reports/20261012_variable64_transaction/user_todo_console/DOCS_BASELINE.zip'])
pack(TX/'MODIFIED_FILE.zip',paths);shutil.copyfile(TX/'BASELINE.zip',TX/'before/MODIFIED_FILE.zip');shutil.copyfile(TX/'MODIFIED_FILE.zip',TX/'after/MODIFIED_FILE.zip')
p=subprocess.run(['git','diff','--no-index','--binary','--','before/MODIFIED_FILE.zip','after/MODIFIED_FILE.zip'],cwd=TX,capture_output=True);assert p.returncode==1;(TX/'DIFF_FILE.patch').write_bytes(p.stdout)
shutil.copyfile(TX/'BASELINE.zip',TX/'reconstruct/MODIFIED_FILE.zip');p=subprocess.run(['git','apply','-p2',str(TX/'DIFF_FILE.patch')],cwd=TX/'reconstruct',capture_output=True);assert p.returncode==0 and sha(TX/'reconstruct/MODIFIED_FILE.zip')==sha(TX/'MODIFIED_FILE.zip')
shutil.copyfile(TX/'MODIFIED_FILE.zip',TX/'restored.zip');p=subprocess.run(['C:/Program Files/Git/bin/bash.exe',str(TX/'ROLLBACK.sh'),str(TX/'restored.zip')],capture_output=True);assert p.returncode==0 and sha(TX/'restored.zip')==sha(TX/'BASELINE.zip')
with zipfile.ZipFile(TX/'MODIFIED_FILE.zip') as z:
 assert z.testzip() is None
 for n in z.namelist():assert z.read(n)==(ROOT/n).read_bytes(),n
old['user_todo_console_extension']={'new_file':str(ROOT/'test/docs/用户尚未测试的待办事项.md'),'three_state':audit,'resource_policy':'current ~283MiB growth accepted; >2GB growth severe, not total process size','power_loss_required':False,'gui_visual_user_pending':True,'console_status':'feasibility only; no console/IPC implementation or runtime tests','source_basis':['process_block.c MinHook CreateProcess interception','Plugin_Log file output','exec_console_command.js native handler discovery and command results'],'proposal':'independent local console; incremental log tail; current-user restricted duplex pipe; bounded queue; verified game execution context','docs_rollback_exact':True,'full_package_rollback_exact':True,'patch_exact':True,'production_unchanged':True}
old['latest_modified_hashes']={n:sha(ROOT/n) for n in paths};(TX/'VERIFICATION.txt').write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8')
roles={}
for n in ['MODIFIED_FILE.zip','DIFF_FILE.patch','VERIFICATION.txt','ROLLBACK.sh']:
 p=TX/n;b=p.read_bytes();roles[n]={'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)};print(json.dumps(roles[n],ensure_ascii=False))
(TX/'artifact_hashes.json').write_text(json.dumps(roles,ensure_ascii=False,indent=2),encoding='utf-8')
c=read(TX/'checkpoint.json');c['user_acceptance_policy']={'resource_growth_severe_threshold':'2GB incremental, not total process size; current growth accepted','power_loss_required':False,'user_only_todo':str(ROOT/'test/docs/用户尚未测试的待办事项.md'),'external_console':'feasible design documented, not implemented'}
c['NEXT_EXECUTABLE_ACTION']='User-only GUI/interaction checks are documented; resource/power-loss policy updated. External console implementation is proposed but awaits an explicit implementation request; do not automatically run the superseded resource-blocking investigation.'
(TX/'checkpoint.json').write_text(json.dumps(c,ensure_ascii=False,indent=2),encoding='utf-8');print('USER_TODO_CONSOLE_DOCS_VERIFIED')
