import sys, os, time, json, hashlib, subprocess, pathlib, re
ROOT=pathlib.Path(r'D:/SteamLibrary/steamapps/common/Hearts of Iron IV/hoi4plugins')
sys.path.insert(0,str(ROOT/'test/tools'))
import hoi4_launch as HL
sys.stdout.reconfigure(encoding="utf-8",errors="replace")
OUT=ROOT/'test/reports/20261012_variable64_reproduction'
if os.environ.get('HOI4_REPRO_PHASE'):
 OUT=OUT/os.environ['HOI4_REPRO_PHASE']
OUT.mkdir(exist_ok=True)
DOC=pathlib.Path(r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV')
GL=DOC/'logs/game.log'
PL=pathlib.Path(HL.LOG)
def capture(label):
 for p,n in [(GL,'game'),(PL,'plugin'),(DOC/'logs/error.log','error')]:
  if p.exists(): (OUT/(label+'_'+n+'.log')).write_bytes(p.read_bytes())
def run(args):
 p=subprocess.run(args,capture_output=True,text=True,encoding='utf-8',errors='replace')
 print('COMMAND',args,'EXIT',p.returncode,'STDOUT',p.stdout,'STDERR',p.stderr,flush=True)
 if p.returncode: raise RuntimeError('command failed')
 if 'numtest_run_command.py' in ' '.join(args) and 'out->ok     = 1' not in p.stdout:
  raise RuntimeError('console command rejected or raised an exception')
 return p.stdout
def wait_game(reload=False):
 t=time.time()
 while time.time()-t<240:
  s=GL.read_text(encoding='utf-8',errors='replace') if GL.exists() else ''
  if ('End RestoreDeviceObjects' if reload else 'Launching SINGLEPLAYER-game') in s:
   print('game marker observed; initialization grace 32s',flush=True); time.sleep(32);return
  if not HL.proc_alive():raise RuntimeError('game died')
  time.sleep(.5)
 raise TimeoutError('game marker')
HL.kill()
capture('before')
run([HL.MSBUILD,str(ROOT/'hoi4plugins.sln'),'/p:Configuration=Release','/p:Platform=x64','/v:minimal','/nologo'])
print('DEPLOY',HL.deploy(),flush=True)
for f in HL.DEPLOY:
 print('DLL',f,hashlib.sha256((pathlib.Path(HL.ROOT)/f).read_bytes()).hexdigest(),flush=True)
fixture=DOC/'mod/bakaifa/events/zz_variable64_reproduction.txt'
fixture.write_text('''add_namespace = zzv64repro
country_event = {
 id = zzv64repro.1
 hidden = yes
 is_triggered_only = yes
 immediate = {
  set_variable = { repro_marker = 12026 }
  set_variable64 = { var = repro_big value = 92233720368546.05 }
  set_variable64 = { var = repro_small value = 1.5 }
  set_variable64 = { var = repro_neg value = -1.5 }
  set_variable64 = { var = repro_zero value = 0 }
  log = "REPRO WRITE marker=[?repro_marker] big=[?repro_big] small=[?repro_small] neg=[?repro_neg] zero=[?repro_zero]"
 }
 option = { name = zzv64repro.1.a }
}
country_event = {
 id = zzv64repro.2
 hidden = yes
 is_triggered_only = yes
 immediate = {
  log = "REPRO READ marker=[?repro_marker] big=[?repro_big] small=[?repro_small] neg=[?repro_neg] zero=[?repro_zero]"
  log_variable64 = { var = repro_big }
  log_variable64 = { var = repro_small }
  log_variable64 = { var = repro_neg }
  log_variable64 = { var = repro_zero }
 }
 option = { name = zzv64repro.2.a }
}
''',encoding='utf-8')
print('FIXTURE',fixture,flush=True)
HL.launch(args=['-gdpr-compliant','-start_tag=ABY','-nolauncher','-force_text_save'],wait_marker='[plugin] Camera_RegisterCommands',timeout=240)
wait_game()
run([sys.executable,'-u',str(ROOT/'test/modules/console/numtest_trigger_events.py'),'zzdatetest.97','zzdatetest.96','zzdatetest.95','zzdatetest.93','zzdatetest.88','zzdatetest.89','zzdatetest.91','zzdatetest.92','zzv64repro.1'])
capture('baseline')
save_start=time.time()
run([sys.executable,'-u',str(ROOT/'test/modules/console/numtest_run_command.py'),'savegame','v64repro12'])
time.sleep(3)
capture('saved')
sv=DOC/'save games/v64repro12.hoi4'
if not sv.exists() or sv.stat().st_mtime<save_start:
 raise RuntimeError('fresh save file was not created')
(OUT/'save_snapshot.hoi4').write_bytes(sv.read_bytes()); print('SAVE',sv,sv.stat().st_size,flush=True)
HL.kill()
HL.launch(args=['-continuelastsave','-nolauncher','-force_text_save'],wait_marker='[plugin] Camera_RegisterCommands',timeout=240)
wait_game(True)
run([sys.executable,'-u',str(ROOT/'test/modules/console/numtest_trigger_events.py'),'zzv64repro.2'])
capture('reload')
print('FINISHED alive=',HL.proc_alive(),flush=True)
