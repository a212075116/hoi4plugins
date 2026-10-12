import argparse,json,pathlib,re,sys,time
from decimal import Decimal
ROOT=pathlib.Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'test/lib'));sys.path.insert(0,str(ROOT/'test/tools'))
import hoi4_launch as HL
import frida_host as FH
DOC=pathlib.Path(r'C:/Users/a2120/Documents/Paradox Interactive/Hearts of Iron IV')
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
TEXT='''add_namespace = zzarraydesign
country_event = { id = zzarraydesign.1 hidden = yes is_triggered_only = yes immediate = {
 clear_array = ad_native
 set_variable64 = { var = ad_native value = 12345678901.125 }
 add_to_array = { array = ad_native value = 2.5 }
 add_to_array = { array = ad_native value = 7.75 }
 add_to_array = { array = ad_native value = -0.125 index = 1 }
 log = "AD inserted=[?ad_native^0],[?ad_native^1],[?ad_native^2] scalar=[?ad_native]"
 remove_from_array = { array = ad_native value = -0.125 }
 log = "AD deleted=[?ad_native^0],[?ad_native^1] scalar=[?ad_native]"
 set_variable = { ad_marker = 20261012 }
 log = "AD WRITE DONE"
 } option = { name = zzarraydesign.1.a } }
country_event = { id = zzarraydesign.2 hidden = yes is_triggered_only = yes immediate = {
 log = "AD restored=[?ad_native^0],[?ad_native^1] scalar=[?ad_native] marker=[?ad_marker]"
 log = "AD RELOAD DONE"
 } option = { name = zzarraydesign.2.a } }
'''
def read(p):return p.read_text(encoding='utf-8',errors='replace') if p.exists() else ''
def ready(reload=False):
 end=time.time()+240;marker='End RestoreDeviceObjects' if reload else 'Launching SINGLEPLAYER-game'
 while marker not in read(DOC/'logs/game.log'):
  if time.time()>end or not HL.proc_alive():raise RuntimeError('readiness')
  time.sleep(.5)
 time.sleep(32)
def execute(out,label,event,save=False):
 pid,s,sc,_=FH.connect(str(ROOT/'test/lib/exec_console_command.js'),force_spawn=False);commands=[]
 try:
  x=sc.exports_sync.exec('event',[event]);assert 'out->ok     = 1' in x;commands.append({'input':event,'stdout':x});print(x,flush=True);time.sleep(.5)
  if save:
   t=time.time();x=sc.exports_sync.exec('savegame',['adproto']);assert 'out->ok     = 1' in x;commands.append({'input':'savegame adproto','stdout':x});print(x,flush=True)
   p=DOC/'save games/adproto.hoi4';end=time.time()+30
   while not p.exists() or p.stat().st_mtime<t:
    if time.time()>end:raise RuntimeError('fresh save missing')
    time.sleep(.2)
   (out/'save_snapshot.hoi4').write_bytes(p.read_bytes())
 finally:FH.detach(s)
 (out/(label+'_commands.json')).write_text(json.dumps(commands,ensure_ascii=False,indent=2),encoding='utf-8')
 for p,n in [(DOC/'logs/game.log','game'),(DOC/'logs/error.log','error'),(pathlib.Path(HL.LOG),'plugin')]:
  if p.exists():(out/(label+'_'+n+'.log')).write_bytes(p.read_bytes())
def verify(out):
 g=read(out/'write_game.log');r=read(out/'reload_game.log');rows=[]
 for key,text,expected in [('inserted',g,['2.5','-0.125','7.75']),('deleted',g,['2.5','7.75']),('restored',r,['2.5','7.75'])]:
  found=re.findall(r'AD '+key+r'=(\S+) scalar=(\S+)',text);parts=found[-1][0].split(',') if found else []
  rows.append({'key':key,'observed':parts,'expected':expected,'ok':len(parts)==len(expected) and all(Decimal(a)==Decimal(b) for a,b in zip(parts,expected))})
  rows.append({'key':key+'.scalar_isolated','observed':found[-1][1] if found else None,'ok':bool(found) and Decimal(found[-1][1])==Decimal('12345678901.125')})
 errors=[l for label in ['write','reload'] for l in read(out/(label+'_error.log')).splitlines() if 'zz_array_design' in l]
 result={'checks':len(rows),'passed':sum(x['ok'] for x in rows),'rows':rows,'errors':errors,'marker_ok':'marker=20261012' in r,'alive':HL.proc_alive(),'integrated_array64':False};result['exit']=int(result['passed']!=len(rows) or bool(errors) or not result['marker_ok'] or not result['alive'])
 (out/'comparison.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2));return result['exit']
def main():
 p=argparse.ArgumentParser();p.add_argument('phase');p.add_argument('--verify-only',action='store_true');a=p.parse_args();out=ROOT/'test/reports/20261012_variable64_transaction/array_design'/a.phase;out.mkdir(parents=True,exist_ok=True)
 if a.verify_only:return verify(out)
 if (out/'write_game.log').exists():raise RuntimeError('preserve phase')
 (out/'events.txt').write_text(TEXT,encoding='utf-8');(DOC/'mod/bakaifa/events/zz_array_design.txt').write_text(TEXT,encoding='utf-8')
 HL.launch(args=['-gdpr-compliant','-start_tag=ABY','-nolauncher','-force_text_save'],wait_marker='[plugin] Camera_RegisterCommands',timeout=240);ready();execute(out,'write','zzarraydesign.1',True)
 HL.launch(args=['-continuelastsave','-nolauncher','-force_text_save'],wait_marker='[plugin] Camera_RegisterCommands',timeout=240);ready(True);execute(out,'reload','zzarraydesign.2');return verify(out)
if __name__=='__main__':raise SystemExit(main())
