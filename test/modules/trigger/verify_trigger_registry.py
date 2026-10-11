import argparse,hashlib,json,os,pathlib,re,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'test/tools'));sys.path.insert(0,str(ROOT/'test/lib'))
import hoi4_launch as HL
import frida_host as FH
DOC=pathlib.Path(r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV')
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
cases=[('true_yes','plugin_trigger_true = yes',1),('true_no','plugin_trigger_true = no',0),
 ('false_yes','plugin_trigger_false = yes',0),('false_no','plugin_trigger_false = no',1),
 ('not_true','NOT = { plugin_trigger_true = yes }',0),('not_false','NOT = { plugin_trigger_false = yes }',1),
 ('and_false','AND = { plugin_trigger_true = yes plugin_trigger_false = yes }',0),
 ('or_true','OR = { plugin_trigger_false = yes plugin_trigger_true = yes }',1),
 ('and_true','AND = { plugin_trigger_true = yes plugin_trigger_false = no }',1),
 ('or_false','OR = { plugin_trigger_true = no plugin_trigger_false = yes }',0),
 ('nested','OR = { AND = { plugin_trigger_true = yes plugin_trigger_true = no } NOT = { plugin_trigger_false = yes } }',1),
 ('scope_yes','plugin_trigger_scope = yes',1),('scope_no','plugin_trigger_scope = no',0),
 ('vanilla_yes','always = yes',1),('vanilla_no','always = no',0),
 ('nested_not','NOT = { NOT = { plugin_trigger_true = yes } }',1),
 ('other_country','ARI = { plugin_trigger_scope = yes }',1)]
def fixture(stress=False):
 lines=['add_namespace = zztriggerreg','country_event = { id = zztriggerreg.1 hidden = yes is_triggered_only = yes immediate = {']
 for key,condition,want in cases:
  lines += ['set_variable = { tr_%s = 0 }'%key,'if = { limit = { %s } set_variable = { tr_%s = 1 } }'%(condition,key),'log = "TRREG %s=[?tr_%s]"'%(key,key)]
 lines+=['log = "TRREG DONE"','} option = { name = zztriggerreg.1.a } }']
 if stress:
  lines+=['country_event = { id = zztriggerreg.2 hidden = yes is_triggered_only = yes immediate = {',
          'set_variable = { tr_bulk_yes = 0 }','set_variable = { tr_bulk_no = 0 }','set_variable = { tr_repeat_yes = 0 }','set_variable = { tr_repeat_no = 0 }']
  for i in range(256):
   lines+=['if = { limit = { plugin_trigger_bulk_%03d = yes } add_to_variable = { tr_bulk_yes = 1 } }'%i,
           'if = { limit = { plugin_trigger_bulk_%03d = no } add_to_variable = { tr_bulk_no = 1 } }'%i]
  for i in range(1000):
   lines+=['if = { limit = { AND = { plugin_trigger_true = yes plugin_trigger_false = no } } add_to_variable = { tr_repeat_yes = 1 } }',
           'if = { limit = { OR = { plugin_trigger_true = no plugin_trigger_false = yes } } add_to_variable = { tr_repeat_no = 1 } }']
  lines+=['log = "TRSTRESS bulk_yes=[?tr_bulk_yes] bulk_no=[?tr_bulk_no] repeat_yes=[?tr_repeat_yes] repeat_no=[?tr_repeat_no]"','log = "TRSTRESS DONE"','} option = { name = zztriggerreg.2.a } }']
 return '\n'.join(lines)+'\n'
def read(p):return p.read_text(encoding='utf-8',errors='replace') if p.exists() else ''
def main():
 ap=argparse.ArgumentParser();ap.add_argument('phase');ap.add_argument('--verify-only',action='store_true');ap.add_argument('--stress',action='store_true');args=ap.parse_args()
 out=ROOT/'test/reports/20261012_variable64_transaction/trigger'/args.phase;out.mkdir(parents=True,exist_ok=True)
 if not args.verify_only:
  if (out/'game.log').exists():raise RuntimeError('keep prior evidence; use a fresh phase name')
  text=fixture(args.stress);(out/'events.txt').write_text(text,encoding='utf-8')
  (DOC/'mod/bakaifa/events/zz_trigger_registry.txt').write_text(text,encoding='utf-8')
  for language in ['english','simp_chinese']:
   loc=DOC/('mod/bakaifa/localisation/zz_trigger_registry_l_'+language+'.yml')
   loc.parent.mkdir(parents=True,exist_ok=True)
   loc.write_text('l_'+language+':\n PLUGIN_TRIGGER_TRUE:0 "Plugin true predicate"\n PLUGIN_TRIGGER_FALSE:0 "Plugin false predicate"\n PLUGIN_TRIGGER_SCOPE:0 "Plugin scope predicate"\n',encoding='utf-8-sig')
  print('DEPLOY',HL.deploy(),flush=True)
  if args.stress:os.environ['HOI4_TRIGGER_REG_STRESS']='1'
  else:os.environ.pop('HOI4_TRIGGER_REG_STRESS',None)
  for name in HL.DEPLOY:
   deployed=(pathlib.Path(HL.ROOT)/name).read_bytes()
   assert deployed==(pathlib.Path(HL.BUILD)/name).read_bytes()
   print('DEPLOY_SHA256',name,hashlib.sha256(deployed).hexdigest(),flush=True)
  HL.launch(args=['-gdpr-compliant','-start_tag=ABY','-nolauncher','-force_text_save'],wait_marker='[plugin] Camera_RegisterCommands',timeout=240)
  deadline=time.time()+240
  while 'Launching SINGLEPLAYER-game' not in read(DOC/'logs/game.log'):
   if not HL.proc_alive():raise RuntimeError('game died')
   if time.time()>deadline:raise TimeoutError('in-game marker')
   time.sleep(.5)
  time.sleep(32)
  pid,session,sc,_=FH.connect(str(ROOT/'test/lib/exec_console_command.js'),force_spawn=False)
  try:
   result=sc.exports_sync.exec('event',['zztriggerreg.1']);print(result,flush=True)
   (out/'command.txt').write_text(result,encoding='utf-8')
   deadline=time.time()+20
   while 'TRREG DONE' not in read(DOC/'logs/game.log') and time.time()<deadline:time.sleep(.2)
   if args.stress:
    result=sc.exports_sync.exec('event',['zztriggerreg.2']);print(result,flush=True)
    deadline=time.time()+60
    while 'TRSTRESS DONE' not in read(DOC/'logs/game.log') and time.time()<deadline:time.sleep(.1)
  finally:FH.detach(session)
  for p,n in [(DOC/'logs/game.log','game'),(DOC/'logs/error.log','error'),(pathlib.Path(HL.LOG),'plugin')]:
   if p.exists():(out/(n+'.log')).write_bytes(p.read_bytes())
 g=read(out/'game.log');rows=[]
 for key,condition,want in cases:
  found=re.findall(r'TRREG '+key+r'=([^\s]+)',g)
  observed=found[-1] if found else None
  rows.append({'key':key,'expected':want,'observed':observed,'ok':observed==str(want)})
 errors=[l for l in read(out/'error.log').splitlines() if 'zz_trigger_registry' in l or 'plugin_trigger_' in l]
 selfcheck='selfcheck: repeat=3 count=3/3 builtin_collision=0' in read(out/'plugin.log')
 stress_ok=True
 if args.stress:
  stress_ok='stress startup registered=256/256 total=259' in read(out/'plugin.log')
  wanted='TRSTRESS bulk_yes=256 bulk_no=0 repeat_yes=1000 repeat_no=0'
  stress_ok=stress_ok and wanted in g
 result={'checks':len(rows),'passed':sum(x['ok'] for x in rows),'rows':rows,'fixture_errors':errors,'registry_selfcheck':selfcheck,'stress_ok':stress_ok,'alive':HL.proc_alive()}
 (out/'comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result['passed']==len(rows) and not errors and selfcheck and stress_ok else 1
if __name__=='__main__':raise SystemExit(main())
