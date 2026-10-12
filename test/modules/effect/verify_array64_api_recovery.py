import argparse, hashlib, json, pathlib, re, struct, sys, time
import verify_array64_api as API
R=API.R; ROOT=API.ROOT; TX=API.TX
SCOPES=[('country','',''),('other','ARI',''),('state','335',''),('character','ABY_Hoshino',''),('global','','global.')]
sys.stdout.reconfigure(encoding='utf-8',errors='replace')

def event(number,lines):
    return 'country_event = { id = zzapr64.'+str(number)+' hidden = yes is_triggered_only = yes immediate = {\n'+'\n'.join(lines)+'\n} option = { name = zzapr64.a } }\n'

def wrap(scope,lines): return [scope+' = {']+lines+['}'] if scope else lines

def check(lines,label,var,value,want=True):
    lines.extend(['set_variable = { apr_ok = 0 }','if = { limit = { check_array64 = { var = '+var+' value = '+str(value)+' compare = equals } } set_variable = { apr_ok = 1 } }','log = "APR '+label+' ok=[?apr_ok]"'])

def reload_pressure():
    lines=[]
    for label,scope,p in SCOPES:
        body=[]
        for suffix,index,value in [('saved_count','num',256),('saved_first','0','12345678901.125'),('saved_tail','255',0)]:check(body,label+'.'+suffix,p+'pressure^'+index,value)
        lines+=wrap(scope,body)
    check(lines,'saved_limit','limitcase^num',4096)
    return event(7,lines)

def setup():
    lines=[];pressure=[]
    for label,scope,p in SCOPES:
        body=['create_array64 = { var = '+p+'prf value = 1 }','set_array_element64 = { var = '+p+'prf^0 value = 12345678901.125 }','append_array64 = { var = '+p+'prf value = -0.00001 }',
              'create_array64 = { var = '+p+'prs value = 1 }','set_array_element64 = { var = '+p+'prs^0 value = 2.5 }']
        check(body,label+'.setup',''+p+'prf^0','12345678901.125');lines+=wrap(scope,body)
        body=['create_array64 = { var = '+p+'pressure value = 0 }']
        for i in range(32):
            body+=['append_array64 = { var = '+p+'pressure value = 12345678901.125 }','insert_array64 = { var = '+p+'pressure^0 value = -0.00001 }','set_array_element_native = { var = '+p+'pressure^1 value = 2.5 }','set_array_element64 = { var = '+p+'pressure^1 value = 12345678901.125 }','erase_array64 = { var = '+p+'pressure^0 value = 0 }']
        check(body,label+'.pressure_count',p+'pressure^num',32);check(body,label+'.pressure_last',p+'pressure^31','12345678901.125')
        body+=['resize_array64 = { var = '+p+'pressure value = 256 }']
        check(body,label+'.resize256',p+'pressure^num',256);check(body,label+'.tail_zero',p+'pressure^255',0)
        pressure+=wrap(scope,body)
    pressure+=['create_array64 = { var = limitcase value = 4096 }']
    check(pressure,'limit4096','limitcase^num',4096)
    pressure+=['append_array64 = { var = limitcase value = 1 }','log = "APR limit_append status=[?__v64sys_status]"','set_array_element64 = { var = limitcase^4096 value = 1 }','log = "APR limit_index status=[?__v64sys_status]"','resize_array64 = { var = limitcase value = 4097 }','log = "APR limit_size status=[?__v64sys_status]"']
    check(pressure,'limit_unchanged','limitcase^num',4096)
    return 'add_namespace = zzapr64\n'+event(1,lines)+event(2,pressure)+reload_pressure()

def exec_event(out,label,number,save=False):
    import frida
    session=R.FH.attach(R.FH.find_pid()) if hasattr(R.FH,'attach') else frida.attach(R.FH.find_pid())
    sc=session.create_script((ROOT/'test/lib/exec_console_command.js').read_text(encoding='utf-8'));cmd=[];start=time.monotonic()
    try:
        sc.load()
        text=sc.exports_sync.exec('event',['zzapr64.'+str(number)]);cmd.append({'input':'event zzapr64.'+str(number),'stdout':text});print(label,text,flush=True);assert 'out->ok     = 1' in text
        if save:
            before=time.time();text=sc.exports_sync.exec('savegame',['apr64']);cmd.append({'input':'savegame apr64','stdout':text});assert 'out->ok     = 1' in text
            target=R.DOC/'save games/apr64.hoi4';end=time.time()+40
            while not target.exists() or target.stat().st_mtime<before:
                if time.time()>end:raise RuntimeError('fresh save missing')
                time.sleep(.2)
            (out/(label+'_save.hoi4')).write_bytes(target.read_bytes())
    finally:R.FH.detach(session)
    for source,name in [(R.DOC/'logs/game.log','game'),(R.DOC/'logs/error.log','error'),(pathlib.Path(R.HL.LOG),'plugin')]:
        if source.exists():(out/(label+'_'+name+'.log')).write_bytes(source.read_bytes())
    (out/(label+'_commands.json')).write_text(json.dumps({'commands':cmd,'seconds':time.monotonic()-start},indent=2),encoding='utf-8')

def launch(reload=False):
    R.HL.launch(args=(['-continuelastsave'] if reload else ['-gdpr-compliant','-start_tag=ABY'])+['-nolauncher','-force_text_save'],wait_marker='[plugin] Camera_RegisterCommands',timeout=240);R.ready(reload)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase');parser.add_argument('--verify-only',action='store_true');args=parser.parse_args();out=TX/'api'/args.phase
    if args.verify_only:return verify(out)
    if out.exists():raise RuntimeError('preserve existing phase')
    out.mkdir(parents=True);fixture=R.DOC/'mod/bakaifa/events/zz_array64_api_recovery.txt';text=setup();fixture.write_text(text,encoding='utf-8');(out/'events.txt').write_text(text,encoding='utf-8');print('DEPLOY',R.HL.deploy(),flush=True);launch();exec_event(out,'setup',1,True)
    save=(out/'setup_save.hoi4').read_text(encoding='utf-8-sig');scopes=[]
    # Each freshly created group has its own unique, pointer-free container identity.
    journalroot=pathlib.Path(R.HL.ROOT)/'reports/array64_journal'
    for path in journalroot.glob('*/prf.a64j'):
        data=path.read_bytes();words=[int(path.parent.name[i:i+8],16) for i in range(0,32,8)]
        if all(re.search(r'__v64sys_id'+str(i)+r'\s*=\s*'+str(w)+r'(?:\.0+)?\s',save) for i,w in enumerate(words)):
            scopes.append({'path':str(path),'data':data,'nonce':list(struct.unpack_from('<4I',data,88)),'generation':struct.unpack_from('<i',data,24)[0]})
    assert len(scopes)==5,len(scopes)
    (out/'sidecar_index.json').write_text(json.dumps([{k:v for k,v in x.items() if k!='data'} for x in scopes],indent=2),encoding='utf-8')
    for i,x in enumerate(scopes):(out/('journal_'+str(i)+'.a64j')).write_bytes(x['data'])
    # Use native script variables to simulate a persisted interrupted append, not a real process crash.
    inject=[];recover=[];normal=[]
    for label,scope,p in SCOPES:
        body=['recover_array64 = { var = '+p+'prf value = 0 }','log = "APR '+label+'.recover status=[?'+p+'__v64sys_status]"']
        check(body,label+'.recover_value',p+'prf^0','12345678901.125');check(body,label+'.recover_count',p+'prf^num',2)
        normal+=wrap(scope,body)
    # Assign the matching journal by logging the actual scope identity, then parse the log.
    ids=[]
    for label,scope,p in SCOPES:ids+=wrap(scope,['log = "APR ID '+label+' '+','.join('[?'+p+'__v64sys_id'+str(i)+']' for i in range(4))+'"'])
    text+=event(3,normal)+event(4,ids)
    fixture.write_text(text,encoding='utf-8');launch(True);exec_event(out,'identities',4)
    idmap=dict(re.findall(r'APR ID (\S+) ([\d,]+)',R.read(out/'identities_game.log')))
    for label,scope,p in SCOPES:
        folder=''.join('%08X'%int(w) for w in idmap[label].split(','));x=next(x for x in scopes if pathlib.Path(x['path']).parent.name==folder)
        body=['set_variable = { '+p+'__v64a_prf_gen = '+str(x['generation']+1)+' }','set_variable = { '+p+'__v64t_prf_p = 1 }']
        for i,w in enumerate(x['nonce']):body+=['set_variable = { '+p+'__v64t_prf_n'+str(i)+' = '+str(w)+' }']
        body+=['set_variable = { '+p+'__v64a_prf_lo^0 = 7 }']
        check(body,label+'.quarantined',p+'prf^0',0,False);inject+=wrap(scope,body)
        body=['recover_array64 = { var = '+p+'prf value = 0 }','log = "APR '+label+'.interrupted status=[?'+p+'__v64sys_status]"']
        check(body,label+'.restored_value',p+'prf^0','12345678901.125');check(body,label+'.restored_count',p+'prf^num',1)
        body+=['recover_array64 = { var = '+p+'prf value = 0 }','log = "APR '+label+'.repeat status=[?'+p+'__v64sys_status]"'];check(body,label+'.repeat_value',p+'prf^0','12345678901.125');recover+=wrap(scope,body)
    text+=event(5,inject)+event(6,recover);fixture.write_text(text,encoding='utf-8')
    exec_event(out,'normal',3)
    anomalies=[]
    for mode in ['missing','truncated','checksum','foreign','oversize']:
        try:
            for x in scopes:
                path=pathlib.Path(x['path']);original=x['data']
                if mode=='missing':path.unlink()
                elif mode=='truncated':path.write_bytes(original[:64])
                elif mode=='checksum':path.write_bytes(original[:-1]+bytes([original[-1]^1]))
                elif mode=='foreign':path.write_bytes((path.parent/'prs.a64j').read_bytes())
                else:path.write_bytes(b'X'*100001)
            exec_event(out,mode,3)
            statuses=re.findall(r'APR (\S+)\.recover status=(-?\d+)',R.read(out/(mode+'_game.log')))[-5:]
            anomalies+= [{'mode':mode,'scope':label,'status':int(code),'ok':int(code)==(-903 if mode in ['missing','truncated','oversize'] else -1)} for label,code in statuses]
            assert len(statuses)==5
        finally:
            for x in scopes:pathlib.Path(x['path']).write_bytes(x['data'])
    launch(True);exec_event(out,'inject',5,True);launch(True);exec_event(out,'recover',6);exec_event(out,'pressure',2,True)
    launch(True);exec_event(out,'reload',6);exec_event(out,'pressure_reload',7)
    (out/'events.txt').write_text(text,encoding='utf-8')
    return verify(out)

def verify(out):
    rows=[]
    for phase in ['setup','normal','inject','recover','pressure','reload','pressure_reload','missing','truncated','checksum','foreign','oversize']:
        suffixes={'setup':['setup'],'normal':['recover_value','recover_count'],'inject':['quarantined'],'recover':['restored_value','restored_count','repeat_value'],'reload':['restored_value','restored_count','repeat_value'],'pressure':['pressure_count','pressure_last','resize256','tail_zero'],'pressure_reload':['saved_count','saved_first','saved_tail']}.get(phase,['recover_value','recover_count'])
        wanted={label+'.'+suffix for label,_,_ in SCOPES for suffix in suffixes}
        if phase=='pressure':wanted.update(['limit4096','limit_unchanged'])
        if phase=='pressure_reload':wanted.add('saved_limit')
        logs=R.read(out/(phase+'_game.log'));pairs=[(key,value) for key,value in dict(re.findall(r'APR (\S+) ok=(\d+)',logs)).items() if key in wanted]
        for label,observed in pairs:
            if phase=='reload' and label.endswith('recover_count'):continue
            want='0' if label.endswith('quarantined') else '1';rows.append({'phase':phase,'key':label,'observed':observed,'want':want,'ok':observed==want})
        observed=dict(pairs)
        for label,_,_ in SCOPES:
            for suffix in suffixes:
                key=label+'.'+suffix;rows.append({'phase':phase,'key':key+'.present','ok':key in observed})
    for mode in ['missing','truncated','checksum','foreign','oversize']:
        observed=dict(re.findall(r'APR (\S+)\.recover status=(-?\d+)',R.read(out/(mode+'_game.log'))))
        for label,_,_ in SCOPES:
            code=observed.get(label);rows.append({'mode':mode,'scope':label,'status':code,'ok':code==('-903' if mode in ['missing','truncated','oversize'] else '-1')})
    for phase in ['normal','recover','reload']:
        for label,code in re.findall(r'APR (\S+) status=(-?\d+)',R.read(out/(phase+'_game.log'))):rows.append({'phase':phase,'key':label,'observed':code,'ok':code=='0'})
    observed=dict(re.findall(r'APR (limit_\S+) status=(-?\d+)',R.read(out/'pressure_game.log')))
    for label in ['limit_append','limit_index','limit_size']:
        code=observed.get(label);rows.append({'key':label,'observed':code,'ok':code==('-901' if label=='limit_size' else '-1')})
    for label in ['limit4096','limit_unchanged']:
        rows.append({'key':label+'.present','ok':label in dict(re.findall(r'APR (\S+) ok=(\d+)',R.read(out/'pressure_game.log')))})
    ops=re.findall(r'\[array64\] (\w+) name=pressure status=(-?\d+)',R.read(out/'pressure_plugin.log'))
    rows.append({'key':'pressure_all_810_operations_success','observed_operations':len(ops),'ok':len(ops)==810 and all(code=='0' for _,code in ops)})
    rows.append({'key':'saved_limit.present','ok':'saved_limit' in dict(re.findall(r'APR (\S+) ok=(\d+)',R.read(out/'pressure_reload_game.log')))})
    errors=[l for phase in ['setup','normal','inject','recover','pressure','reload'] for l in R.read(out/(phase+'_error.log')).splitlines() if 'zz_array64_api_recovery' in l]
    result={'checks':len(rows),'passed':sum(x['ok'] for x in rows),'rows':rows,'fixture_errors':errors,'alive':R.HL.proc_alive(),'dll_sha256':hashlib.sha256((pathlib.Path(R.HL.ROOT)/'hoi4_mod_plugin.dll').read_bytes()).hexdigest(),'simulated_interruption_not_real_crash':True,'pressure_cycles_per_scope':32,'pressure_scopes':5}
    result['exit']=int(result['checks']!=result['passed'] or bool(errors) or not result['alive']);(out/'comparison.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2));return result['exit']

if __name__=='__main__':raise SystemExit(main())
