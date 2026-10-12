import hashlib,json,pathlib,shutil,subprocess,sys,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[3];TX=ROOT/'test/reports/20261012_variable64_transaction';D=TX/'camera_unify'
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
native=read(D/'native_final/comparison.json');assert native['exit']==0 and native['checks']==native['passed']
assert read(D/'unit_modified_extended/result.json')['exit']==0
old=read(TX/'VERIFICATION.txt');changed={'src/plugin/SDK_RVA/effect/effect_camera.c','src/plugin/SDK_RVA/effect/effect_reg.c','src/plugin/SDK_RVA/effect/effect_reg.h'}
for n,h in old['latest_modified_hashes'].items():
 if n.startswith('src/') and n not in changed:assert sha(ROOT/n)==h,n
dll=ROOT.parent/'hoi4_mod_plugin.dll';assert sha(dll)==native['dll_sha256']==sha(ROOT/'build/Release/hoi4_mod_plugin.dll')
shutil.copyfile(dll,D/'hoi4_mod_plugin.MODIFIED.dll')
(TX/'CURRENT_BUILD.json').write_text(json.dumps({'dll_archive':'test/reports/20261012_variable64_transaction/camera_unify/hoi4_mod_plugin.MODIFIED.dll','sha256':sha(dll),'reason':'camera shared setter and corrected generic Effect tooltip append ABI'},indent=2),encoding='utf-8')
restored=D/'restored.camera-effect.c';shutil.copyfile(ROOT/'src/plugin/SDK_RVA/effect/effect_camera.c',restored)
p=subprocess.run(['C:/Program Files/Git/bin/bash.exe',str(TX/'ROLLBACK.sh'),str(restored)],capture_output=True);assert p.returncode==0
assert restored.read_bytes()==(D/'effect_camera.BASELINE.c').read_bytes()
p=subprocess.run([sys.executable,str(ROOT/'test/modules/camera/test_camera_effect_shared.py'),str(restored),str(D/'unit_rollback_extended')],capture_output=True);assert p.returncode==1
for suffix,name in [('camera-tooltip.c','effect_reg.c'),('camera-tooltip.h','effect_reg.h')]:
 copy=D/('restored.'+suffix);shutil.copyfile(ROOT/'src/plugin/SDK_RVA/effect'/name,copy)
 p=subprocess.run(['C:/Program Files/Git/bin/bash.exe',str(TX/'ROLLBACK.sh'),str(copy)],capture_output=True);assert p.returncode==0 and copy.read_bytes()==(D/name.replace('.', '.BASELINE.',1)).read_bytes()
with zipfile.ZipFile(TX/'MODIFIED_FILE.zip') as z:paths=set(z.namelist())
paths.update(['test/modules/camera/test_camera_effect_shared.py','test/modules/camera/verify_camera_effect_shared.py','test/modules/camera/finalize_camera_effect_shared.py','test/reports/20261012_variable64_transaction/CURRENT_BUILD.json','test/reports/20261012_variable64_transaction/camera_unify/hoi4_mod_plugin.MODIFIED.dll','ai_docs/08_Effect系统/摄像机Effect与控制台路径统一.md'])
with zipfile.ZipFile(TX/'MODIFIED_FILE.zip','w',zipfile.ZIP_DEFLATED) as z:
 for n in sorted(paths):
  i=zipfile.ZipInfo(n,(2026,10,12,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;z.writestr(i,(ROOT/n).read_bytes())
shutil.copyfile(TX/'BASELINE.zip',TX/'before/MODIFIED_FILE.zip');shutil.copyfile(TX/'MODIFIED_FILE.zip',TX/'after/MODIFIED_FILE.zip')
p=subprocess.run(['git','diff','--no-index','--binary','--','before/MODIFIED_FILE.zip','after/MODIFIED_FILE.zip'],cwd=TX,capture_output=True);assert p.returncode==1
(TX/'DIFF_FILE.patch').write_bytes(p.stdout);shutil.copyfile(TX/'BASELINE.zip',TX/'reconstruct/MODIFIED_FILE.zip')
p=subprocess.run(['git','apply','-p2',str(TX/'DIFF_FILE.patch')],cwd=TX/'reconstruct',capture_output=True);assert p.returncode==0 and sha(TX/'reconstruct/MODIFIED_FILE.zip')==sha(TX/'MODIFIED_FILE.zip')
shutil.copyfile(TX/'MODIFIED_FILE.zip',TX/'restored.zip');p=subprocess.run(['C:/Program Files/Git/bin/bash.exe',str(TX/'ROLLBACK.sh'),str(TX/'restored.zip')],capture_output=True);assert p.returncode==0 and sha(TX/'restored.zip')==sha(TX/'BASELINE.zip')
with zipfile.ZipFile(TX/'MODIFIED_FILE.zip') as z:
 assert z.testzip() is None
 for n in z.namelist():assert z.read(n)==(ROOT/n).read_bytes()
old['camera_shared_extension']={'symbol':'CameraEffect_WriteHeight -> Camera_SetHeight; remove async limit parameter rewrite; Effect_BuildTooltip append ABI','native':native,'units':{label:read(D/('unit_'+label+'_extended/result.json')) for label in ['baseline','modified','rollback']},'baseline_source_sha256':sha(D/'effect_camera.BASELINE.c'),'current_source_sha256':sha(ROOT/'src/plugin/SDK_RVA/effect/effect_camera.c'),'dll_sha256':sha(dll),'native_commands':read(D/'native_final/commands.json'),'scope_regression':read(TX/'scope/camera_shared_final/comparison.json'),'trigger_regression':read(D/'trigger_regression/result.json'),'build_stdout':(D/'build_final.stdout.txt').read_text(encoding='utf-8'),'build_stderr':(D/'build_final.stderr.txt').read_text(encoding='utf-8'),'build_exit':0,'retained_errors':{p:(D/p).read_text(encoding='utf-8') for p in ['native_v1_console.txt','native_short_console.txt','native_localized_console.txt','native_loc_fixed_console.txt']},'ida_append_evidence':read(D/'0x14011DBC0_fresh.json'),'source_rollback_exact':True,'full_package_rollback_exact':True,'patch_reconstructs_exact_package':True,'visual_verified':False,'resource_leak_cause_verified':False}
old['latest_modified_hashes']={n:sha(ROOT/n) for n in paths};(TX/'VERIFICATION.txt').write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8')
roles={}
for n in ['MODIFIED_FILE.zip','DIFF_FILE.patch','VERIFICATION.txt','ROLLBACK.sh']:
 p=TX/n;b=p.read_bytes();roles[n]={'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)};print(json.dumps(roles[n],ensure_ascii=False))
(TX/'artifact_hashes.json').write_text(json.dumps(roles,ensure_ascii=False,indent=2),encoding='utf-8');print('CAMERA_SHARED_TRANSACTION_VERIFIED')
