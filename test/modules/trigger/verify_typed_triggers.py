import json,pathlib,re,sys,time,argparse
ROOT=pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'test/tools'));sys.path.insert(0,str(ROOT/'test/lib'))
import hoi4_launch as HL
import frida_host as FH
DOC=pathlib.Path(r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV')
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
cases=[]
def fixture():
 cases.clear()
 lines=['add_namespace = zztypedtrg','country_event = { id = zztypedtrg.1 hidden = yes is_triggered_only = yes immediate = {',
 'set_variable64 = { var = tt_root value = 2.5 }','set_variable64 = { var = global.tt_global value = 3.75 }']
 def check(key,condition,want):
  cases.append((key,want));lines.extend(['set_variable = { tt_result = 0 }','if = { limit = { '+condition+' } set_variable = { tt_result = 1 } }','log = "TYPED '+key+'=[?tt_result]"'])
 for key,condition,want in [('scalar_gt','plugin_value_half > 0.49999',1),('scalar_lt','plugin_value_half < 0.50001',1),
  ('scalar_gt_equal','plugin_value_half > 0.5',0),('scalar_lt_equal','plugin_value_half < 0.5',0),
  ('scalar_not','NOT = { plugin_value_half > 0.5 }',1),('scalar_variable','plugin_value_half < ROOT.tt_root',1)]:check(key,condition,want)
 for label,block in [('country',''),('other','ARI'),('state','335'),('character','ABY_Hoshino')]:
  if block:lines.append(block+' = {')
  lines+=['set_variable64 = { var = tt_value value = 12345678901.125 }','set_variable64 = { var = tt_rhs value = 12345678901.125 }',
          'set_variable64 = { var = tt_negative value = -2.5 }']
  for comp,want in [('equals',1),('not_equals',0),('less_than',0),('greater_than',0),('less_than_or_equals',1),('greater_than_or_equals',1)]:
   check(label+'_'+comp,'plugin_check_variable64 = { var = tt_value value = tt_rhs compare = '+comp+' }',want)
  check(label+'_fraction','plugin_check_variable64 = { var = tt_value value = 12345678901.12499 compare = greater_than }',1)
  check(label+'_negative','plugin_check_variable64 = { var = tt_negative value = -2.50001 compare = greater_than }',1)
  check(label+'_root','plugin_check_variable64 = { var = ROOT.tt_root value = 2.5 compare = equals }',1)
  check(label+'_global','plugin_check_variable64 = { var = global.tt_global value = 3.75 compare = equals }',1)
  check(label+'_not','NOT = { plugin_check_variable64 = { var = tt_value value = tt_rhs compare = not_equals } }',1)
  check(label+'_vanilla','check_variable = { var = tt_negative value = -2 compare = less_than }',0)
  lines.append('log = "TYPED '+label+'_unchanged=[?tt_value]"')
  if block:lines.append('}')
 check('rhs_root','ARI = { plugin_check_variable64 = { var = ROOT.tt_root value = ROOT.tt_root compare = equals } }',1)
 check('rhs_global','plugin_check_variable64 = { var = ROOT.tt_root value = global.tt_global compare = less_than }',1)
 check('native_fallback','plugin_check_variable64 = { var = 2.5 value = 2.5 compare = equals }',1)
 lines+=['log = "TYPED DONE"','} option = { name = zztypedtrg.1.a } }']
 lines+=['country_event = { id = zztypedtrg.2 hidden = yes is_triggered_only = yes immediate = {',
 'set_variable = { tt_repeat_yes = 0 }','set_variable = { tt_repeat_no = 0 }']
 for i in range(1000):
  lines+=['if = { limit = { AND = { plugin_value_half > 0.49999 plugin_check_variable64 = { var = tt_value value = 12345678901.125 compare = equals } } } add_to_variable = { tt_repeat_yes = 1 } }',
          'if = { limit = { OR = { plugin_value_half < 0.5 plugin_check_variable64 = { var = tt_value value = 12345678901.125 compare = not_equals } } } add_to_variable = { tt_repeat_no = 1 } }']
 lines+=['log = "TYPRESS yes=[?tt_repeat_yes] no=[?tt_repeat_no]"',
 'if = { limit = { NOT = { plugin_check_variable64 = { } } } log = "TYPRESS empty_false=1" }',
 'if = { limit = { NOT = { plugin_check_variable64 = { var = tt_value } } } log = "TYPRESS missing_rhs_false=1" }',
 'ARI = { if = { limit = { plugin_check_variable64 = { var = ROOT.tt_root value = PREV.tt_root compare = equals } } log = "TYPRESS prev=1" } }',
 'set_variable64 = { var = tt_from value = 4.5 }','ARI = { country_event = { id = zztypedtrg.3 } }',
 'log = "TYPRESS DONE"','} option = { name = zztypedtrg.2.a } }',
 'country_event = { id = zztypedtrg.3 hidden = yes is_triggered_only = yes immediate = {',
 'if = { limit = { plugin_check_variable64 = { var = FROM.tt_from value = 4.5 compare = equals } } log = "TYPRESS from=1" }',
 'log = "TYPRESS CHILD DONE"','} option = { name = zztypedtrg.3.a } }']
 return '\n'.join(lines)+'\n'
def read(p):return p.read_text(encoding='utf-8',errors='replace') if p.exists() else ''
def verify(out):
 g=read(out/'game.log');e=read(out/'error.log');p=read(out/'plugin.log');fixture()
 rows=[]
 for key,want in cases:
  got=re.findall(r'TYPED '+key+r'=(\S+)',g);value=got[-1] if got else None
  rows.append({'key':key,'expected':want,'observed':value,'ok':value==str(want)})
 errors=[l for l in e.splitlines() if 'zz_typed_triggers' in l or 'plugin_value_half' in l or 'plugin_check_variable64' in l]
 unchanged=re.findall(r'TYPED (?:country|other|state|character)_unchanged=(\S+)',g)[-4:]
 result={'checks':len(rows),'passed':sum(x['ok'] for x in rows),'rows':rows,'errors':errors,
         'unchanged':unchanged,'registration':'typed templates registered=2 total=5' in p,'alive':HL.proc_alive()}
 result['exit']=0 if result['passed']==len(rows) and not errors and result['registration'] and unchanged==['12345678901.125']*4 and result['alive'] else 1
 (out/'comparison.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2));return result['exit']
def main():
 ap=argparse.ArgumentParser();ap.add_argument('phase');ap.add_argument('--verify-only',action='store_true');ap.add_argument('--deploy',action='store_true');a=ap.parse_args()
 out=ROOT/'test/reports/20261012_variable64_transaction/numeric'/a.phase;out.mkdir(parents=True,exist_ok=True)
 if a.verify_only:return verify(out)
 if (out/'game.log').exists():raise RuntimeError('preserve prior phase')
 text=fixture();(out/'events.txt').write_text(text,encoding='utf-8');(DOC/'mod/bakaifa/events/zz_typed_triggers.txt').write_text(text,encoding='utf-8')
 if a.deploy:print('DEPLOY',HL.deploy(),flush=True)
 HL.launch(args=['-gdpr-compliant','-start_tag=ABY','-nolauncher','-force_text_save'],wait_marker='[plugin] Camera_RegisterCommands',timeout=240)
 deadline=time.time()+240
 while 'Launching SINGLEPLAYER-game' not in read(DOC/'logs/game.log'):
  if time.time()>deadline or not HL.proc_alive():raise RuntimeError('game readiness')
  time.sleep(.5)
 time.sleep(32)
 pid,session,sc,_=FH.connect(str(ROOT/'test/lib/exec_console_command.js'),force_spawn=False)
 try:
  r=sc.exports_sync.exec('event',['zztypedtrg.1']);(out/'command.txt').write_text(r,encoding='utf-8');print(r,flush=True)
  if 'out->ok     = 1' not in r:raise RuntimeError(r)
  deadline=time.time()+20
  while 'TYPED DONE' not in read(DOC/'logs/game.log') and time.time()<deadline:time.sleep(.2)
 finally:FH.detach(session)
 for path,name in [(DOC/'logs/game.log','game'),(DOC/'logs/error.log','error'),(pathlib.Path(HL.LOG),'plugin')]:
  if path.exists():(out/(name+'.log')).write_bytes(path.read_bytes())
 return verify(out)
if __name__=='__main__':raise SystemExit(main())
