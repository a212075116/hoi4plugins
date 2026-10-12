import argparse,hashlib,json,pathlib,re,sys,time
from decimal import Decimal
import verify_array64_transaction as T
R=T.R;ROOT=T.ROOT;TX=T.TX
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
def fixtures():
    write=['add_namespace = zzap64','country_event = { id = zzap64.1 hidden = yes is_triggered_only = yes immediate = {'];reload=['country_event = { id = zzap64.2 hidden = yes is_triggered_only = yes immediate = {'];expected=[]
    def check(lines,label,var,value,want=True):
        lines.extend(['set_variable = { api_ok = 0 }','if = { limit = { check_array64 = { var = '+var+' value = '+value+' compare = equals } } set_variable = { api_ok = 1 } }','log = "API '+label+' ok=[?api_ok]"']);expected.append({'key':label,'want':'1' if want else '0'})
    for label,scope,prefix in [('country','',''),('other','ARI',''),('state','335',''),('character','ABY_Hoshino',''),('global','','global.')]:
        if scope:write.append(scope+' = {');reload.append(scope+' = {')
        name=prefix+'api_array'
        write+=['set_variable64 = { var = '+name+' value = 12345678901.125 }','clear_array = '+name,'add_to_array = { array = '+name+' value = 2.5 }','add_to_array = { array = '+name+' value = 7.75 }',
          'create_array64 = { var = '+name+' value = 2 }']
        check(write,label+'.create_count',name+'^num','2');check(write,label+'.create_zero',name+'^0','0')
        write+=['set_array_element64 = { var = '+name+'^0 value = 12345678901.125 }','append_array64 = { var = '+name+' value = 5000000000.125 }','insert_array64 = { var = '+name+'^1 value = -0.00001 }']
        check(write,label+'.insert',name+'^1','-0.00001');check(write,label+'.append',name+'^3','5000000000.125')
        write+=['erase_array64 = { var = '+name+'^2 value = 0 }','resize_array64 = { var = '+name+' value = 4 }','set_array_element_native = { var = '+name+'^0 value = 2.5 }']
        check(write,label+'.native',name+'^0','2.5');check(write,label+'.neighbor',name+'^1','-0.00001');check(write,label+'.resize_zero',name+'^3','0')
        write+=['set_array_element64 = { var = '+name+'^0 value = 12345678901.125 }','log_array64 = { var = '+name+'^0 value = 0 }',
            'set_variable64 = { var = '+name+'^0 value = 5000000000.125 }','log = "API '+label+'.native_objects scalar=[?'+name+'] a0=[?'+name+'^0] a1=[?'+name+'^1]"']
        check(write,label+'.guard',name+'^0','12345678901.125')
        check(reload,label+'.reload_value',name+'^0','12345678901.125');check(reload,label+'.reload_count',name+'^num','5' if label=='other' else '4');check(reload,label+'.reload_neighbor',name+'^1','-0.00001')
        if scope:write.append('}');reload.append('}')
    # Parsed ROOT scalar64 operands and invalid input leave existing array values intact.
    write+=['set_variable64 = { var = api_rhs value = 5000000000.125 }','ARI = { append_array64 = { var = api_array value = ROOT.api_rhs } }']
    check(write,'root_rhs','ARI.api_array^4','5000000000.125')
    write+=['create_array64 = { var = api_array value = 1 }','log = "API collision_status=[?__v64sys_status]"',
        'insert_array64 = { var = api_array^0.5 value = 1 }','log = "API fractional_index_status=[?__v64sys_status]"',
        'create_array64 = { var = api_negative value = -1 }','log = "API negative_size_status=[?__v64sys_status]"',
        'create_array64 = { var = api_clear value = 1 }','clear_array64 = { var = api_clear value = 0 }','create_array64 = { var = api_clear value = 2 }']
    check(write,'clear_recreate','api_clear^num','2');check(write,'missing_query','api_missing^0','0',False)
    write+=['log = "API WRITE DONE"','} option = { name = zzap64.1.a } }'];reload+=['log = "API RELOAD DONE"','} option = { name = zzap64.2.a } }']
    return '\n'.join(write+reload)+'\n',expected
def execute(out,phase,event,save=False):
    import frida
    s=frida.attach(R.FH.find_pid());sc=s.create_script((ROOT/'test/lib/exec_console_command.js').read_text(encoding='utf-8'));commands=[]
    try:
        sc.load();text=sc.exports_sync.exec('event',[event]);print(text,flush=True);commands.append({'input':'event '+event,'stdout':text});assert 'out->ok     = 1' in text
        if save:
            start=time.time();text=sc.exports_sync.exec('savegame',['ap64']);print(text,flush=True);commands.append({'input':'savegame ap64','stdout':text});assert 'out->ok     = 1' in text
            p=R.DOC/'save games/ap64.hoi4';end=time.time()+30
            while not p.exists() or p.stat().st_mtime<start:
                if time.time()>end:raise RuntimeError('fresh save missing')
                time.sleep(.2)
            (out/'save_snapshot.hoi4').write_bytes(p.read_bytes())
    finally:R.FH.detach(s)
    (out/(phase+'_commands.json')).write_text(json.dumps(commands,indent=2),encoding='utf-8')
    for p,n in [(R.DOC/'logs/game.log','game'),(R.DOC/'logs/error.log','error'),(pathlib.Path(R.HL.LOG),'plugin')]:
        if p.exists():(out/(phase+'_'+n+'.log')).write_bytes(p.read_bytes())
def verify(out):
    expected=json.loads(R.read(out/'expected.json'));alltext=R.read(out/'write_game.log')+'\n'+R.read(out/'reload_game.log');observed=dict(re.findall(r'API (\S+) ok=(\S+)',alltext));rows=[]
    for e in expected:rows.append({'key':e['key'],'ok':observed.get(e['key'])==e['want'],'observed':observed.get(e['key']),'want':e['want']})
    for label in ['country','other','state','character','global']:
        match=re.findall(r'API '+label+r'\.native_objects scalar=(\S+) a0=(\S+) a1=(\S+)',alltext);rows.append({'key':label+'.native_isolation','ok':bool(match) and match[-1]==('12345678901.125','2.5','7.75')})
    for key,want in [('collision_status','-2'),('fractional_index_status','-901'),('negative_size_status','-901')]:
        value=(re.findall(r'API '+key+r'=(\S+)',alltext) or [None])[-1];rows.append({'key':key,'ok':value==want,'observed':value})
    plugin=R.read(out/'write_plugin.log');rows.append({'key':'registered','ok':'effects=10/10' in plugin and 'trigger=1/1' in plugin})
    rows.append({'key':'full_precision_log','ok':'api_array^0=12345678901.125' in plugin})
    errors=[l for phase in ['write','reload'] for l in R.read(out/(phase+'_error.log')).splitlines() if 'zz_array64_api' in l]
    rows.append({'key':'fixture_errors','ok':not errors});r={'checks':len(rows),'passed':sum(v['ok'] for v in rows),'rows':rows,'errors':errors,'alive':R.HL.proc_alive(),'deployed_dll_sha256':hashlib.sha256((pathlib.Path(R.HL.ROOT)/'hoi4_mod_plugin.dll').read_bytes()).hexdigest()};r['exit']=int(r['passed']!=r['checks'] or not r['alive']);(out/'comparison.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r,indent=2));return r['exit']
def main():
    p=argparse.ArgumentParser();p.add_argument('phase');p.add_argument('--verify-only',action='store_true');a=p.parse_args();out=TX/'api'/a.phase;out.mkdir(parents=True,exist_ok=True)
    if a.verify_only:return verify(out)
    if (out/'write_game.log').exists():raise RuntimeError('preserve phase')
    text,e=fixtures();(out/'events.txt').write_text(text,encoding='utf-8');(out/'expected.json').write_text(json.dumps(e,indent=2),encoding='utf-8');(R.DOC/'mod/bakaifa/events/zz_array64_api.txt').write_text(text,encoding='utf-8')
    print('DEPLOY',R.HL.deploy(),flush=True)
    R.HL.launch(args=['-gdpr-compliant','-start_tag=ABY','-nolauncher','-force_text_save'],wait_marker='[plugin] Camera_RegisterCommands',timeout=240);R.ready();execute(out,'write','zzap64.1',True)
    R.HL.launch(args=['-continuelastsave','-nolauncher','-force_text_save'],wait_marker='[plugin] Camera_RegisterCommands',timeout=240);R.ready(True);execute(out,'reload','zzap64.2');return verify(out)
if __name__=='__main__':raise SystemExit(main())
