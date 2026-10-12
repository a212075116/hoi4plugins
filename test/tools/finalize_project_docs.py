import hashlib,json,pathlib,shutil,subprocess,sys,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[2];TX=ROOT/'test/reports/20261012_variable64_transaction';D=TX/'docs_audit'
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
old=read(TX/'VERIFICATION.txt')
for name,expected in old['latest_modified_hashes'].items():
 if name.startswith('src/'):assert sha(ROOT/name)==expected,name
assert sha(ROOT.parent/'hoi4_mod_plugin.dll')=='72704dfaa4cc5485425841a19a34f38a866bc88c9f72a7743b1dcc7ca9b41070'
docs=sorted([p for d in ['ai_docs','test/docs'] for p in (ROOT/d).rglob('*.md')])
def pack(path,paths):
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
  for name in sorted(paths):
   info=zipfile.ZipInfo(name,(2026,10,12,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,(ROOT/name).read_bytes())
pack(D/'DOCS_MODIFIED.zip',[p.relative_to(ROOT).as_posix() for p in docs])
shutil.copyfile(D/'DOCS_MODIFIED.zip',D/'restored.docs.zip')
rollback=subprocess.run(['C:/Program Files/Git/bin/bash.exe',str(TX/'ROLLBACK.sh'),str(D/'restored.docs.zip')],capture_output=True);assert rollback.returncode==0
assert sha(D/'restored.docs.zip')==sha(D/'DOCS_BASELINE.zip')
audit={}
for label,p in [('baseline',D/'DOCS_BASELINE.zip'),('modified',D/'DOCS_MODIFIED.zip'),('rollback',D/'restored.docs.zip')]:
 command=[sys.executable,str(ROOT/'test/tools/audit_project_docs.py'),'--package',str(p),'--output',str(D/(label+'_audit.json'))]
 result=subprocess.run(command,capture_output=True);audit[label]={'command':command,'stdout':result.stdout.decode('utf-8'),'stderr':result.stderr.decode('utf-8'),'exit':result.returncode,'result':read(D/(label+'_audit.json'))}
 print(label,'exit',result.returncode,'docs',audit[label]['result']['documents'],'max',audit[label]['result']['max_lines'],'findings',len(audit[label]['result']['findings']))
assert audit['baseline']['exit']==audit['rollback']['exit']==1 and audit['modified']['exit']==0
assert audit['baseline']['result']==audit['rollback']['result']
with zipfile.ZipFile(TX/'MODIFIED_FILE.zip') as z:paths=set(z.namelist())
paths.update(p.relative_to(ROOT).as_posix() for p in docs)
paths.update(['test/tools/audit_project_docs.py','test/tools/reconcile_project_docs.py','test/tools/finalize_project_docs.py','test/reports/20261012_variable64_transaction/docs_audit/DOCS_BASELINE.zip'])
pack(TX/'MODIFIED_FILE.zip',paths)
shutil.copyfile(TX/'BASELINE.zip',TX/'before/MODIFIED_FILE.zip');shutil.copyfile(TX/'MODIFIED_FILE.zip',TX/'after/MODIFIED_FILE.zip')
p=subprocess.run(['git','diff','--no-index','--binary','--','before/MODIFIED_FILE.zip','after/MODIFIED_FILE.zip'],cwd=TX,capture_output=True);assert p.returncode==1
(TX/'DIFF_FILE.patch').write_bytes(p.stdout);shutil.copyfile(TX/'BASELINE.zip',TX/'reconstruct/MODIFIED_FILE.zip')
p=subprocess.run(['git','apply','-p2',str(TX/'DIFF_FILE.patch')],cwd=TX/'reconstruct',capture_output=True);assert p.returncode==0,p.stderr
assert sha(TX/'reconstruct/MODIFIED_FILE.zip')==sha(TX/'MODIFIED_FILE.zip')
shutil.copyfile(TX/'MODIFIED_FILE.zip',TX/'restored.zip');p=subprocess.run(['C:/Program Files/Git/bin/bash.exe',str(TX/'ROLLBACK.sh'),str(TX/'restored.zip')],capture_output=True);assert p.returncode==0
assert sha(TX/'restored.zip')==sha(TX/'BASELINE.zip')
with zipfile.ZipFile(TX/'MODIFIED_FILE.zip') as z:
 assert z.testzip() is None
 for name in z.namelist():assert z.read(name)==(ROOT/name).read_bytes(),name
baseline=read(D/'baseline_inventory.json');current={p.relative_to(ROOT).as_posix():sha(p) for p in docs}
changed=[r['path'] for r in baseline if current.get(r['path'])!=r['sha256']];added=sorted(set(current)-{r['path'] for r in baseline})
old['documentation_audit_extension']={'targets':[str(ROOT/'ai_docs'),str(ROOT/'test/docs')],'original_documents':len(baseline),'documents_after':len(docs),'modified_existing':changed,'added_documents':added,
 'three_state':audit,'original_docs_zip_sha256':sha(D/'DOCS_BASELINE.zip'),'modified_docs_zip_sha256':sha(D/'DOCS_MODIFIED.zip'),'docs_rollback_exact':True,'full_package_rollback_exact':True,'patch_reconstructs_exact_package':True,
 'rollback_command':{'command':rollback.args,'stdout':rollback.stdout.decode('utf-8'),'stderr':rollback.stderr.decode('utf-8'),'exit':rollback.returncode},
 'production_source_changed':False,'production_dll_changed':False,'new_game_tests_executed':False,
 'manual_findings':['Bool-only index replaced by typed+Array64 current state','8-byte raw storage separated from original operation precision; unsupported vendor-version extrapolation withdrawn','Historical CModule phases explicitly scoped; full original long-document bodies retained in six chapter splits','CLI/lib/source paths and root cwd corrected; no-process connect(False) auto-spawn caveat','Camera control path and Effect RVA path differ in current source, not silently declared fixed','Array64 status slot only updates when target container resolved; stale0 is not execution success'],
 'limits':['External URLs, every historical RVA and external mod config not re-executed or re-certified','Historical hypotheses remain explicitly archived rather than deleted','Resource attribution, camera Effect side effects, full GUI/multiplayer/power-loss remain genuinely unverified']}
old['latest_modified_hashes']={name:sha(ROOT/name) for name in sorted(paths)}
(TX/'VERIFICATION.txt').write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8')
roles={}
for n in ['MODIFIED_FILE.zip','DIFF_FILE.patch','VERIFICATION.txt','ROLLBACK.sh']:
 p=TX/n;b=p.read_bytes();roles[n]={'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)};print(json.dumps(roles[n],ensure_ascii=False))
(TX/'artifact_hashes.json').write_text(json.dumps(roles,ensure_ascii=False,indent=2),encoding='utf-8')
checkpoint=read(TX/'checkpoint.json');checkpoint['documentation_audit_completed']={'targets':[str(ROOT/'ai_docs'),str(ROOT/'test/docs')],'documents':len(docs),'max_lines':audit['modified']['result']['max_lines'],'status':'current contracts/paths reconciled; historical chapters explicitly scoped; source divergence retained as pending'}
(TX/'checkpoint.json').write_text(json.dumps(checkpoint,ensure_ascii=False,indent=2),encoding='utf-8')
print('DOCS_TRANSACTION_VERIFIED',len(changed),'existing changed',len(added),'added')
