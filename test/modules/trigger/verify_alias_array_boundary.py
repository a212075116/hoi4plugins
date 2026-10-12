import argparse,json,pathlib,re,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'test/lib'));sys.path.insert(0,str(ROOT/'test/tools'))
import hoi4_launch as HL
import frida_host as FH
DOC=pathlib.Path(r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV')
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
def fixture():
 lines=['add_namespace = zzaliasarray','country_event = { id = zzaliasarray.1 hidden = yes is_triggered_only = yes immediate = {',
 'set_variable = { ba_count = num_owned_states }','log = "BAX count=[?ba_count]"',
 'set_variable64 = { var = num_owned_states value = 12345678901.125 }',
 'clear_array = ba_arr','add_to_array = { array = ba_arr value = 2.5 }','add_to_array = { array = ba_arr value = 7.75 }',
 'set_variable64 = { var = ba_arr value = 12345678901.125 }']
 cases=[('dynamic','num_owned_states','ba_count'),('explicit','var:num_owned_states','12345678901.125'),
        ('index0','ba_arr^0','2.5'),('index1','ba_arr^1','7.75')]
 for key,var,val in cases:
  for typ,trg in [('native','check_variable'),('custom','plugin_check_variable64')]:
   lines+=['set_variable = { ba_result = 0 }','if = { limit = { '+trg+' = { var = '+var+' value = '+val+' compare = equals } } set_variable = { ba_result = 1 } }',
           'log = "BAX '+key+'.'+typ+'=[?ba_result]"']
 lines+=['set_variable64 = { var = ba_arr^0 value = 5000000000.125 }','log = "BAX after_index64 a0=[?ba_arr^0] scalar=[?ba_arr]"',
         'set_variable = { var = ba_arr^1 value = 3.5 }','add_to_variable = { var = ba_arr^1 value = 0.25 }',
         'log = "BAX after_native a1=[?ba_arr^1] scalar=[?ba_arr]"','log = "BAX DONE"','} option = { name = zzaliasarray.1.a } }']
 return '\n'.join(lines)+'\n'
def read(p):return p.read_text(encoding='utf-8',errors='replace') if p.exists() else ''
def verify(out):
 g=read(out/'game.log');rows=[]
 for key in ['dynamic','index0','index1']:
  vals={t:(re.findall(r'BAX '+key+r'\.'+t+r'=(\S+)',g) or [None])[-1] for t in ['native','custom']}
  rows.append({'key':key,'observed':vals,'ok':vals['native']==vals['custom']=='1'})
 v={t:(re.findall(r'BAX explicit\.'+t+r'=(\S+)',g) or [None])[-1] for t in ['native','custom']};rows.append({'key':'explicit_prefix_follows_native','observed':v,'ok':v['native']==v['custom']=='0'})
 a=re.findall(r'BAX after_index64 a0=(\S+) scalar=(\S+)',g);b=re.findall(r'BAX after_native a1=(\S+) scalar=(\S+)',g)
 rows.append({'key':'indexed64_rejected_without_mutation','observed':a,'ok':bool(a) and a[-1]==('2.5','12345678901.125')})
 rows.append({'key':'native_array_and_scalar_isolated','observed':b,'ok':bool(b) and b[-1]==('3.75','12345678901.125')})
 errors=[l for l in read(out/'error.log').splitlines() if 'zz_alias_array' in l];r={'checks':len(rows),'passed':sum(x['ok'] for x in rows),'rows':rows,'errors':errors,'alive':HL.proc_alive()};r['exit']=int(r['passed']!=len(rows) or bool(errors) or not r['alive'])
 (out/'comparison.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r,indent=2));return r['exit']
def main():
 p=argparse.ArgumentParser();p.add_argument('phase');p.add_argument('--deploy',action='store_true');p.add_argument('--verify-only',action='store_true');a=p.parse_args();out=ROOT/'test/reports/20261012_variable64_transaction/boundary'/a.phase;out.mkdir(parents=True,exist_ok=True)
 if a.verify_only:return verify(out)
 if (out/'game.log').exists():raise RuntimeError('preserve phase')
 text=fixture();(out/'events.txt').write_text(text,encoding='utf-8');(DOC/'mod/bakaifa/events/zz_alias_array.txt').write_text(text,encoding='utf-8')
 if a.deploy:print('DEPLOY',HL.deploy(),flush=True)
 HL.launch(args=['-gdpr-compliant','-start_tag=ABY','-nolauncher','-force_text_save'],wait_marker='[plugin] Camera_RegisterCommands',timeout=240)
 end=time.time()+240
 while 'Launching SINGLEPLAYER-game' not in read(DOC/'logs/game.log'):
  if time.time()>end or not HL.proc_alive():raise RuntimeError('readiness')
  time.sleep(.5)
 time.sleep(32);pid,s,sc,_=FH.connect(str(ROOT/'test/lib/exec_console_command.js'),force_spawn=False)
 try:
  x=sc.exports_sync.exec('event',['zzaliasarray.1']);print(x,flush=True);assert 'out->ok     = 1' in x;(out/'command.txt').write_text(x,encoding='utf-8');time.sleep(1)
 finally:FH.detach(s)
 for path,n in [(DOC/'logs/game.log','game'),(DOC/'logs/error.log','error'),(pathlib.Path(HL.LOG),'plugin')]:
  if path.exists():(out/(n+'.log')).write_bytes(path.read_bytes())
 return verify(out)
if __name__=='__main__':raise SystemExit(main())
