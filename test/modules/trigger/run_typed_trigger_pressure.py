import pathlib,sys,json,time,re
ROOT=pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'test/lib'));sys.path.insert(0,str(ROOT/'test/tools'));sys.path.insert(0,str(ROOT/'test/modules/trigger'))
import frida_host as FH
import hoi4_launch as HL
import verify_typed_triggers as T
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
out=ROOT/'test/reports/20261012_variable64_transaction/numeric'/sys.argv[1];out.mkdir(parents=True,exist_ok=True)
if (out/'game.log').exists():raise RuntimeError('preserve prior phase')
pid,session,sc,_=FH.connect(str(ROOT/'test/lib/exec_console_command.js'),force_spawn=False)
commands=[]
try:
 for event in ['zztypedtrg.1','zztypedtrg.2']:
  r=sc.exports_sync.exec('event',[event]);commands.append({'event':event,'stdout':r});print(r,flush=True)
  if 'out->ok     = 1' not in r:raise RuntimeError(r)
 deadline=time.time()+30
 while 'TYPRESS CHILD DONE' not in T.read(T.DOC/'logs/game.log') and time.time()<deadline:time.sleep(.2)
finally:FH.detach(session)
for path,name in [(T.DOC/'logs/game.log','game'),(T.DOC/'logs/error.log','error'),(pathlib.Path(HL.LOG),'plugin')]:
 if path.exists():(out/(name+'.log')).write_bytes(path.read_bytes())
(out/'commands.json').write_text(json.dumps(commands,ensure_ascii=False,indent=2),encoding='utf-8')
typed=T.verify(out);g=T.read(out/'game.log')
markers=['TYPRESS yes=1000 no=0','TYPRESS prev=1','TYPRESS from=1','TYPRESS empty_false=1','TYPRESS missing_rhs_false=1','TYPRESS CHILD DONE']
result={'markers':{k:k in g for k in markers},'typed_exit':typed,'alive':HL.proc_alive()};result['exit']=int(typed!=0 or not all(result['markers'].values()) or not result['alive'])
(out/'pressure.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2));raise SystemExit(result['exit'])
