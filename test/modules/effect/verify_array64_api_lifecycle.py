import argparse,hashlib,json,pathlib,re,struct,sys,time
import verify_array64_api_recovery as P
R=P.R;ROOT=P.ROOT;TX=P.TX;SCOPES=P.SCOPES
sys.stdout.reconfigure(encoding='utf-8',errors='replace')

def event(n,lines):return 'country_event = { id = zzal64.'+str(n)+' hidden = yes is_triggered_only = yes immediate = {\n'+'\n'.join(lines)+'\n} option = { name = zzal64.a } }\n'
def change(p,key,value):return 'set_variable = { '+p+key+' = '+str(value)+' }'
def check(lines,key,var,value,array=True,want=True):
    token='check_array64' if array else 'plugin_check_variable64'
    lines.extend(['set_variable = { al_ok = 0 }','if = { limit = { '+token+' = { var = '+var+' value = '+str(value)+' compare = equals } } set_variable = { al_ok = 1 } }','log = "AL '+key+' ok=[?al_ok]"'])
    return {'key':key,'want':'1' if want else '0'}

def fixtures(records):
    matrix=[];persist=[];badrecover=[];latest=[];old=[];paired=[];expected={i:[] for i in [1,2,3,4,5,6,7]}
    for label,scope,p in SCOPES:
        x=records[label];nonce=x['nonce'];stamps=x['stamps'];words=x['identity'];g=x['generation'];body=[]
        def inject():return [change(p,'__v64a_prf_gen',g+1),change(p,'__v64a_prf_lo^0',7),change(p,'__v64t_prf_p',1)]+[change(p,'__v64t_prf_n'+str(i),w) for i,w in enumerate(nonce)]
        cases=[('nonce','__v64t_prf_n0',nonce[0],-5),('phase','__v64t_prf_p',1,-5),('missing_receipt','__v64t_prf_n2',nonce[2],-5),('branch','__v64o_prf_b0',stamps[0],-7),('incarnation','__v64o_prf_i0',stamps[4],-7),('generation','__v64a_prf_gen',g+1,-6),('identity','__v64sys_id2',words[2],-902)]
        for case,key,original,status in cases:
            tag=label+'.'+case;body+=inject()
            if case in ['missing_receipt','identity']:body+=['clear_variable = '+p+key]
            else:body+=[change(p,key,g+3 if case=='generation' else original%2147483647+1)]
            body+=['recover_array64 = { var = '+p+'prf value = 0 }','log = "AL '+tag+' status=[?'+p+'__v64sys_status]"']
            expected[1].append({'key':tag,'status':str(status)})
            expected[1].append(check(body,tag+'.quarantine',p+'prf^0',0,want=False))
            expected[1].append(check(body,tag+'.low_unchanged',p+'__v64a_prf_lo^0',7,array=False))
            expected[1].append(check(body,tag+'.gen_unchanged',p+'__v64a_prf_gen',g+3 if case=='generation' else g+1,array=False))
            body+=[change(p,key,original),'recover_array64 = { var = '+p+'prf value = 0 }','log = "AL '+tag+'.fixed status=[?'+p+'__v64sys_status]"']
            expected[1].append({'key':tag+'.fixed','status':'0'})
            expected[1].append(check(body,tag+'.restored',p+'prf^0','12345678901.125'))
            expected[1].append(check(body,tag+'.count',p+'prf^num',1))
        matrix+=P.wrap(scope,body)
        body=inject()+[change(p,'__v64t_prf_n0',nonce[0]%2147483647+1),change(p,'__v64o_prf_b0',stamps[0]%2147483647+1)]
        expected[3].append(check(body,label+'.persist_quarantine',p+'prf^0',0,want=False));persist+=P.wrap(scope,body)
        body=['recover_array64 = { var = '+p+'prf value = 0 }','log = "AL '+label+'.saved_bad_nonce status=[?'+p+'__v64sys_status]"',change(p,'__v64t_prf_n0',nonce[0]),'recover_array64 = { var = '+p+'prf value = 0 }','log = "AL '+label+'.saved_bad_branch status=[?'+p+'__v64sys_status]"',change(p,'__v64o_prf_b0',stamps[0]),'recover_array64 = { var = '+p+'prf value = 0 }','log = "AL '+label+'.saved_fixed status=[?'+p+'__v64sys_status]"']
        expected[4]+=[{'key':label+'.saved_bad_nonce','status':'-5'},{'key':label+'.saved_bad_branch','status':'-7'},{'key':label+'.saved_fixed','status':'0'}]
        expected[4].append(check(body,label+'.saved_value',p+'prf^0','12345678901.125'));badrecover+=P.wrap(scope,body)
        body=['set_array_element64 = { var = '+p+'prf^0 value = 2.5 }'];expected[5].append(check(body,label+'.new_value',p+'prf^0','2.5'));latest+=P.wrap(scope,body)
        for lines,num,status in [(old,6,'-5'),(paired,7,'0')]:
            body=['recover_array64 = { var = '+p+'prf value = 0 }','log = "AL '+label+'.pair status=[?'+p+'__v64sys_status]"'];expected[num].append({'key':label+'.pair','status':status})
            expected[num].append(check(body,label+'.old_value',p+'prf^0','12345678901.125'));expected[num].append(check(body,label+'.old_count',p+'prf^num',1));expected[num].append(check(body,label+'.old_gen',p+'__v64a_prf_gen',g+2,array=False));lines+=P.wrap(scope,body)
    # Event 2 uses the same value checks as the paired state, with a foreign sidecar.
    expected[2]=[dict(e,**({'status':'-1'} if 'status' in e else {})) for e in expected[7]]
    text='add_namespace = zzal64\n'+''.join(event(i,lines) for i,lines in [(1,matrix),(2,paired),(3,persist),(4,badrecover),(5,latest),(6,old),(7,paired)])
    return text,expected

def execute(out,label,n,save=None):
    import frida
    session=frida.attach(R.FH.find_pid());sc=session.create_script((ROOT/'test/lib/exec_console_command.js').read_text(encoding='utf-8'));commands=[]
    game=R.DOC/'logs/game.log';plugin=pathlib.Path(R.HL.LOG);before={p:p.read_bytes() if p.exists() else b'' for p in [game,plugin]}
    try:
        sc.load();text=sc.exports_sync.exec('event',['zzal64.'+str(n)]);print(label,text,flush=True);commands.append({'input':'event zzal64.'+str(n),'stdout':text});assert 'out->ok     = 1' in text
        if save:
            start=time.time();text=sc.exports_sync.exec('savegame',[save]);commands.append({'input':'savegame '+save,'stdout':text});assert 'out->ok     = 1' in text
            path=R.DOC/('save games/'+save+'.hoi4');end=time.time()+40
            while not path.exists() or path.stat().st_mtime<start:
                if time.time()>end:raise RuntimeError('fresh save missing')
                time.sleep(.2)
            (out/(label+'_save.hoi4')).write_bytes(path.read_bytes())
    finally:R.FH.detach(session)
    for path,name in [(game,'game'),(plugin,'plugin')]:
        data=path.read_bytes();assert data.startswith(before[path]);(out/(label+'_'+name+'.log')).write_bytes(data[len(before[path]):])
    (out/(label+'_error.log')).write_bytes((R.DOC/'logs/error.log').read_bytes())
    (out/(label+'_commands.json')).write_text(json.dumps(commands,ensure_ascii=False,indent=2),encoding='utf-8')

def snapshot(out,records,label):
    d=out/label;d.mkdir();result={}
    for scope,x in records.items():
        data=pathlib.Path(x['path']).read_bytes();(d/(scope+'.a64j')).write_bytes(data);result[scope]=hashlib.sha256(data).hexdigest()
    return result

def verify(out):
    expected=json.loads((out/'expected.json').read_text(encoding='utf-8'));rows=[]
    for label,number in [('matrix',1),('foreign_scope',2),('persist',3),('restart_bad',4),('latest',5),('old_save_new_sidecar',6),('paired_old',7)]:
        text=R.read(out/(label+'_game.log'));values=dict(re.findall(r'AL (\S+) ok=(\d+)',text));status=dict(re.findall(r'AL (\S+) status=(-?\d+)',text))
        for e in expected[str(number)]:
            want=e.get('want',e.get('status'));got=(values if 'want' in e else status).get(e['key']);rows.append({'phase':label,'key':e['key'],'want':want,'observed':got,'ok':got==want})
    evidence=json.loads((out/'sidecars.json').read_text(encoding='utf-8'))
    rows.append({'key':'rejected_transactions_do_not_write_sidecars','ok':evidence['before']==evidence['after_matrix']})
    rows.append({'key':'old_pair_restored_exact','ok':evidence['before']==evidence['paired']})
    rows.append({'key':'newer_intents_distinct','ok':all(evidence['newer'][k]!=v for k,v in evidence['before'].items())})
    errors=[line for phase in ['matrix','foreign_scope','persist','restart_bad','latest','old_save_new_sidecar','paired_old'] for line in R.read(out/(phase+'_error.log')).splitlines() if 'zz_array64_api_lifecycle' in line]
    result={'checks':len(rows),'passed':sum(x['ok'] for x in rows),'rows':rows,'fixture_errors':errors,'alive':R.HL.proc_alive(),'dll_sha256':hashlib.sha256((ROOT.parent/'hoi4_mod_plugin.dll').read_bytes()).hexdigest(),'simulated_faults_not_forced_crash':True,'visual_hover_verified':False}
    result['exit']=int(result['checks']!=result['passed'] or bool(errors) or not result['alive']);(out/'comparison.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2));return result['exit']

def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase');parser.add_argument('--verify-only',action='store_true');args=parser.parse_args();out=TX/'api'/args.phase
    if args.verify_only:return verify(out)
    if out.exists():raise RuntimeError('preserve existing phase')
    out.mkdir(parents=True);prior=TX/'api/recovery_v3';idmap=dict(re.findall(r'APR ID (\S+) ([\d,]+)',R.read(prior/'identities_game.log')));index=json.loads((prior/'sidecar_index.json').read_text(encoding='utf-8'));records={}
    for label,_,_ in SCOPES:
        words=[int(w) for w in idmap[label].split(',')];folder=''.join('%08X'%w for w in words);x=next(x for x in index if pathlib.Path(x['path']).parent.name==folder);data=pathlib.Path(x['path']).read_bytes()
        assert struct.unpack_from('<i',data,24)[0]==x['generation']==4
        records[label]={**x,'identity':words,'stamps':list(struct.unpack_from('<8I',data,56))}
    text,expected=fixtures(records);(out/'events.txt').write_text(text,encoding='utf-8');(out/'expected.json').write_text(json.dumps(expected,indent=2),encoding='utf-8');(out/'records.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    (R.DOC/'mod/bakaifa/events/zz_array64_api_lifecycle.txt').write_text(text,encoding='utf-8')
    evidence={'before':snapshot(out,records,'original')};P.launch(True);execute(out,'matrix',1);evidence['after_matrix']=snapshot(out,records,'after_matrix')
    originals={label:(out/'original'/(label+'.a64j')).read_bytes() for label,_,_ in SCOPES}
    try:
        for i,(label,x) in enumerate(records.items()):pathlib.Path(x['path']).write_bytes(originals[list(records)[(i+1)%5]])
        execute(out,'foreign_scope',2)
    finally:
        for label,x in records.items():pathlib.Path(x['path']).write_bytes(originals[label])
    execute(out,'persist',3,'l64bad');P.launch(True);execute(out,'restart_bad',4,'l64old');execute(out,'latest',5);evidence['newer']=snapshot(out,records,'newer')
    P.launch(True);execute(out,'old_save_new_sidecar',6)
    for label,x in records.items():pathlib.Path(x['path']).write_bytes(originals[label])
    execute(out,'paired_old',7);evidence['paired']=snapshot(out,records,'paired');(out/'sidecars.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    return verify(out)

if __name__=='__main__':raise SystemExit(main())
