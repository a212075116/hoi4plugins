import argparse,hashlib,json,os,pathlib,re,sys,time
import verify_array64_transaction as T
import verify_array64_recovery as C
R=T.R;ROOT=T.ROOT;TX=T.TX;SOURCE=ROOT/'src/plugin/SDK_RVA/variable64/array64_durable_snapshot.c'
SCOPES=['country:ABY','country:ARI','state:335','character:ABY_Hoshino','global']
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
def expanded():return SOURCE.read_text(encoding='utf-8').replace('#include "array64_recovery.c"',C.expanded())
def fixtures():
    expected=[];prep=['add_namespace = zzads','country_event = { id = zzads.1 hidden = yes is_triggered_only = yes immediate = {'];fault=['country_event = { id = zzads.2 hidden = yes is_triggered_only = yes immediate = {'];reload=['country_event = { id = zzads.3 hidden = yes is_triggered_only = yes immediate = {']
    for sid,(label,scope,prefix) in enumerate([('country','',''),('other','ARI',''),('state','335',''),('character','ABY_Hoshino',''),('global','','global.')],1):
        for lines in [prep,fault,reload]:
            if scope:lines.append(scope+' = {')
        prep+=['set_variable = { '+prefix+'ds_scopeid = '+str(sid)+' }','set_variable = { '+prefix+'ds_lineage = 20261012 }']
        for case in ['persist','stale']:
            name='tx'+case;root=prefix+'__v64a_'+name
            prep+=['set_variable64 = { var = '+prefix+name+' value = 12345678901.125 }','clear_array = '+prefix+name,
                'add_to_array = { array = '+prefix+name+' value = 2.5 }','add_to_array = { array = '+prefix+name+' value = 7.75 }']
            for suffix,v in [('ver',2),('gen',2),('len',2)]:prep.append('set_variable = { '+root+'_'+suffix+' = '+str(v)+' }')
            for col,suffix in enumerate(['lo','hi','kind']):
                prep.append('clear_array = '+root+'_'+suffix)
                for triple in [T.G.split(1234567890112500),T.G.split(-1)]:prep.append('add_to_array = { array = '+root+'_'+suffix+' value = '+str(triple[col])+' }')
            for lines,marker in [(prep,'dp_'),(fault,'dq_'),(reload,'dr_')]:
                lines.append('if = { limit = { plugin_check_variable64 = { var = '+prefix+marker+name+' value = 0 compare = equals } } log = "DS '+label+'.'+case+' scalar=[?'+prefix+name+'] a0=[?'+prefix+name+'^0] a1=[?'+prefix+name+'^1]" }')
            expected.append({'scope':SCOPES[sid-1],'sid':sid,'label':label,'name':name,'case':case})
        for lines in [prep,fault,reload]:
            if scope:lines.append('}')
    for lines,event in [(prep,1),(fault,2),(reload,3)]:lines+=['log = "DS EVENT '+str(event)+' DONE"','} option = { name = zzads.'+str(event)+'.a } }']
    return '\n'.join(prep+fault+reload)+'\n',expected
def probe(address,records):
    js=T.probe(address).replace('const source='+json.dumps(T.expanded()),'const source='+json.dumps(expanded()))
    at=js.index('function capture(self,ctx)');end=js.index('rpc.exports.samples=()=>rows;',at)
    extra='const records='+json.dumps(records)+';\nconst scopes='+json.dumps(SCOPES)+';\n'+r'''
const size=new NativeFunction(cm.Array64_SnapshotBytes,'uint',[])();
const cap=new NativeFunction(cm.Array64_Capture,'int',['pointer','pointer','int','uint64','pointer']);
const exportRecord=new NativeFunction(cm.Array64_ExportBaseline,'int',['pointer','pointer','uint64','pointer','uint','pointer']);
const importRecord=new NativeFunction(cm.Array64_ImportBaseline,'int',['pointer','pointer','pointer','uint64','uint64','pointer','uint','pointer']);
const recover=new NativeFunction(cm.Array64_Recover,'int',['pointer','pointer','uint64','pointer','int']);
const prepared=new Map();
function blob(hex){const data=Uint8Array.from(hex.match(/../g).map(s=>parseInt(s,16))),p=Memory.alloc(data.length);p.writeByteArray(data);return{p,bytes:data.length};}
function exportOne(c,name,scope,lineage,gen,owner){const snap=Memory.alloc(size),buffer=Memory.alloc(100000),n=Memory.alloc(4);n.writeU32(0);const captured=cap(c,Memory.allocUtf8String(name),gen,owner,snap),result=exportRecord(snap,Memory.allocUtf8String(scope),lineage,buffer,100000,n);if(captured!==1||result!==1)throw Error('export');return{captured,result,hex:bytes(buffer,n.readU32()),bytes:n.readU32()};}
function importOne(c,name,scope,lineage,record,owner){const snap=Memory.alloc(size),b=blob(record),result=importRecord(c,Memory.allocUtf8String(name),Memory.allocUtf8String(scope),lineage,owner,b.p,b.bytes,snap);return{result,snap};}
function capture(self,ctx){try{const d=self.add(88),n=txt(d.add(112));if(!/^(dp|dq|dr)_tx/.test(n))return;const name=n.slice(3),extra=Array.from({length:8},()=>Memory.alloc(8)),c=resolve(d,ctx,...extra),id=c.toString()+n;if(seen.has(id))return;seen.add(id);
 const sid=Number(slot(c,'ds_scopeid').readS64().toString())/100000,lineage=new UInt64(slot(c,'ds_lineage').readS64().toString()),scope=scopes[sid-1];if(!scope)throw Error('resolved fixture scope');
 const owner=new UInt64(5000+rows.length),before=snap(c),protectedBefore=protectedSnap(c,name),start=writes.length,key=scope+'|'+name,steps=[];let record=null,old=null;
 if(n.startsWith('dp_')){
   const first=exportOne(c,name,scope,lineage,2,owner);
   if(name==='txstale'){old=first;const result=setGroup(c,Memory.allocUtf8String(name),0,2,new Int64('-9223372036854775808'),1,0,0);steps.push({key:'prepare_commit',result});record=exportOne(c,name,scope,lineage,4,owner);}else record=first;
   prepared.set(key,{generation:name==='txstale'?4:2});
 }else if(n.startsWith('dq_')){
   if(!prepared.has(key))throw Error('records must be exported first');const gen=prepared.get(key).generation;
   const result=setGroup(c,Memory.allocUtf8String(name),0,gen,new Int64('9223372036854775807'),1,5,1);steps.push({key:'quarantine',result});
 }else{
   if(!records[key])throw Error('record missing');const hex=records[key].record;
   const checks=[{key:'scope',scope:scope==='global'?'country:ABY':'global',lineage,hex,want:-4},
     {key:'lineage',scope,lineage:lineage.add(1),hex,want:-4},
     {key:'corrupt',scope,lineage,hex:hex.slice(0,-2)+(hex.endsWith('00')?'01':'00'),want:-3},
     {key:'version',scope,lineage,hex:hex.slice(0,16)+'02000000'+hex.slice(24),want:-2},
     {key:'truncated',scope,lineage,hex:hex.slice(0,-2),want:-3}];
   if(records[key].old)checks.push({key:'stale',scope,lineage,hex:records[key].old,want:-5});
   const foreign=Object.entries(records).find(([k])=>k.endsWith('|'+name)&&!k.startsWith(scope+'|'));
   if(foreign)checks.push({key:'foreign_record',scope,lineage,hex:foreign[1].record,want:-4});
   for(const test of checks){const beforeTest=snap(c),w=writes.length,result=importOne(c,name,test.scope,test.lineage,test.hex,owner).result;steps.push({key:test.key,result,want:test.want,noWrite:beforeTest===snap(c)&&w===writes.length});}
   const loaded=importOne(c,name,scope,lineage,hex,owner);steps.push({key:'import',result:loaded.result});if(loaded.result!==1)throw Error('valid import');
   const result=recover(c,Memory.allocUtf8String(name),owner,loaded.snap,0);steps.push({key:'recover',result});
   const beforeReplay=snap(c),w=writes.length,replay=importOne(c,name,scope,lineage,hex,new UInt64(9999)).result;steps.push({key:'file_replay',result:replay,want:-5,noWrite:beforeReplay===snap(c)&&w===writes.length});
 }
 rows.push({phase:n.slice(0,2),name,scope,container:c.toString(),lineage:lineage.toString(),record,old,steps,after:group(c,name),onlyExpectedSlotsChanged:protectedBefore===protectedSnap(c,name),sameBytes:before===snap(c),writes:writes.slice(start)});
}catch(e){rows.push({error:String(e)});}}
'''
    return js[:at]+extra+js[end:]
def persist(out,samples):
    result={};folder=out/'records';folder.mkdir(exist_ok=True)
    for s in samples:
        if s.get('phase')!='dp':continue
        key=s['scope']+'|'+s['name'];result[key]={'record':s['record']['hex']}
        if s['old']:result[key]['old']=s['old']['hex']
        for kind,hexvalue in list(result[key].items()):
            p=folder/(str(len(result))+'_'+kind+'.a64');b=bytes.fromhex(hexvalue);temp=p.with_suffix('.tmp')
            with open(temp,'wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
            os.replace(temp,p);assert p.read_bytes()==b
            result[key][kind+'_path']=str(p.resolve());result[key][kind+'_sha256']=hashlib.sha256(b).hexdigest()
    (out/'records.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result
def loaded_records(out):
    manifest=json.loads(R.read(out/'records.json'));result={}
    for key,info in manifest.items():
        result[key]={}
        for kind in ['record','old']:
            if kind not in info:continue
            b=pathlib.Path(info[kind+'_path']).read_bytes();assert hashlib.sha256(b).hexdigest()==info[kind+'_sha256'];result[key][kind]=b.hex()
    return result
def inspect_record(data,key):
    assert data[:8]==b'A64BASE2' and int.from_bytes(data[8:12],'little')==1 and int.from_bytes(data[12:16],'little')==2
    length=int.from_bytes(data[16:20],'little');gen=int.from_bytes(data[20:24],'little');sl=int.from_bytes(data[32:36],'little');nl=int.from_bytes(data[36:40],'little')
    assert length<=4096 and gen<=2147483644 and gen%2==0 and 0<sl<=80 and 0<nl<=20 and len(data)==48+sl+nl+24*length
    h=14695981039346656037
    for value in data[:-8]:h=((h^value)*1099511628211)&((1<<64)-1)
    assert h==int.from_bytes(data[-8:],'little')
    scope=data[40:40+sl].decode('ascii');name=data[40+sl:40+sl+nl].decode('ascii');assert scope+'|'+name==key
    pos=40+sl+nl;raws=[]
    for index in range(length):
        lo,hi,kind=[int.from_bytes(data[pos+index*24+j*8:pos+index*24+(j+1)*8],'little',signed=True) for j in range(3)]
        if kind==0:assert hi==0;raws.append(str(lo));continue
        assert kind in [100000,200000,300000,400000] and lo%100000==hi%100000==0
        low,high=lo//100000,hi//100000;flags=kind//100000-1
        if flags&1:assert low==0;low=-(1<<31)
        if flags&2:assert high==0;high=-(1<<31)
        raws.append(str(high*(1<<32)+(low&0xffffffff)))
    return {'scope':scope,'name':name,'generation':gen,'raws':raws}
def execute(out,phase):
    import frida
    addr=re.findall(r'\[trg\] \+ plugin_check_variable64.*eval=([0-9A-Fa-f]+)',R.read(pathlib.Path(R.HL.LOG)))[-1];records=loaded_records(out) if phase=='reload' else {}
    (out/(phase+'_backend.c')).write_text(expanded(),encoding='utf-8');s=frida.attach(R.FH.find_pid());sc=s.create_script(probe(addr,records));commands=[]
    try:
        sc.load()
        for event in (['zzads.1','zzads.2'] if phase=='write' else ['zzads.3']):
            text=sc.exports_sync.exec('event',[event]);print(text,flush=True);commands.append({'input':'event '+event,'stdout':text});assert 'out->ok     = 1' in text
            samples=sc.exports_sync.samples()
            if event=='zzads.1':persist(out,samples);commands.append({'input':'persist baseline files before quarantine','files_reopened':len(loaded_records(out))})
        (out/(phase+'_samples.json')).write_text(json.dumps(sc.exports_sync.samples(),indent=2),encoding='utf-8')
        if phase=='write':
            start=time.time();text=sc.exports_sync.exec('savegame',['ads']);print(text,flush=True);commands.append({'input':'savegame ads','stdout':text});assert 'out->ok     = 1' in text
            p=R.DOC/'save games/ads.hoi4';end=time.time()+30
            while not p.exists() or p.stat().st_mtime<start:
                if time.time()>end:raise RuntimeError('fresh save missing')
                time.sleep(.2)
            (out/'save_snapshot.hoi4').write_bytes(p.read_bytes())
    finally:R.FH.detach(s)
    (out/(phase+'_commands.json')).write_text(json.dumps(commands,indent=2),encoding='utf-8')
    for p,n in [(R.DOC/'logs/game.log','game'),(R.DOC/'logs/error.log','error'),(pathlib.Path(R.HL.LOG),'plugin')]:
        if p.exists():(out/(phase+'_'+n+'.log')).write_bytes(p.read_bytes())
def verify(out):
    e=json.loads(R.read(out/'expected.json'));write=json.loads(R.read(out/'write_samples.json'));reload=json.loads(R.read(out/'reload_samples.json'));rows=[]
    for phase,samples in [('write',write),('reload',reload)]:
        rows.append({'key':phase+'.source','ok':R.read(out/(phase+'_backend.c'))==expanded()});rows.append({'key':phase+'.captures','ok':len(samples)==(20 if phase=='write' else 10) and not any('error' in s for s in samples)})
        selected=[s for s in samples if s.get('phase')==('dq' if phase=='write' else 'dr')]
        for expected,s in zip(e,selected):
            h=s.get('after',{}).get('head',{});good=s.get('scope')==expected['scope'] and s.get('name')==expected['name'] and s.get('onlyExpectedSlotsChanged')
            if phase=='write':good=good and h.get('status')==-5 and s['steps'][0]['result']==-3
            else:good=good and h.get('status')==1 and h.get('generation')==(6 if expected['case']=='stale' else 4) and [v['raw'] for v in s['after']['values']]==(['-9223372036854775808','-1'] if expected['case']=='stale' else ['1234567890112500','-1'])
            rows.append({'key':phase+'.'+expected['label']+'.'+expected['case'],'ok':bool(good),'observed':s})
            for step in s.get('steps',[]):rows.append({'key':phase+'.'+expected['label']+'.'+expected['case']+'.'+step['key'],'ok':step['result']==step.get('want',1 if step['key'] in ['import','recover'] else -3) and step.get('noWrite',True)})
            g=R.read(out/(phase+'_game.log'));m=re.findall(r'DS '+re.escape(expected['label']+'.'+expected['case'])+r' scalar=(\S+) a0=(\S+) a1=(\S+)',g);rows.append({'key':phase+'.'+expected['label']+'.'+expected['case']+'.native','ok':bool(m) and m[-1]==('12345678901.125','2.5','7.75')})
    before={s['scope']+'|'+s['name']:s['container'] for s in write if s.get('phase')=='dq'}
    rows.append({'key':'fresh_container_binding','ok':all(before.get(s['scope']+'|'+s['name'])!=s['container'] for s in reload)})
    rows.append({'key':'disk_record_reopen','ok':len(loaded_records(out))==10})
    for key,items in loaded_records(out).items():
        for kind,hexvalue in items.items():
            decoded=inspect_record(bytes.fromhex(hexvalue),key);wide=key.endswith('|txstale') and kind=='record'
            rows.append({'key':'wire_oracle.'+key+'.'+kind,'ok':decoded['generation']==(4 if wide else 2) and decoded['raws']==(['-9223372036854775808','-1'] if wide else ['1234567890112500','-1']),'decoded':decoded})
    errors=[l for phase in ['write','reload'] for l in R.read(out/(phase+'_error.log')).splitlines() if 'zz_array_durable' in l];rows.append({'key':'parser_errors','ok':not errors})
    r={'checks':len(rows),'passed':sum(s['ok'] for s in rows),'rows':rows,'errors':errors,'expanded_sha256':hashlib.sha256(expanded().encode()).hexdigest(),'alive':R.HL.proc_alive(),'public_api':False,'semantic_identity_source':'trusted fixture scope labels independently indexed by persisted ds_scopeid in resolved native containers; not identity derived from file'};r['exit']=int(r['passed']!=r['checks'] or not r['alive']);(out/'comparison.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in r.items() if k!='rows'},indent=2));print('FAILED',json.dumps([s for s in rows if not s['ok']],indent=2));return r['exit']
def main():
    p=argparse.ArgumentParser();p.add_argument('phase');p.add_argument('--verify-only',action='store_true');a=p.parse_args();out=TX/'array_durable'/a.phase;out.mkdir(parents=True,exist_ok=True)
    if a.verify_only:return verify(out)
    if (out/'write_samples.json').exists():raise RuntimeError('preserve phase')
    text,e=fixtures();(out/'events.txt').write_text(text,encoding='utf-8');(out/'expected.json').write_text(json.dumps(e,indent=2),encoding='utf-8');(R.DOC/'mod/bakaifa/events/zz_array_durable.txt').write_text(text,encoding='utf-8')
    R.HL.launch(args=['-gdpr-compliant','-start_tag=ABY','-nolauncher','-force_text_save'],wait_marker='[plugin] Camera_RegisterCommands',timeout=240);R.ready();execute(out,'write')
    R.HL.launch(args=['-continuelastsave','-nolauncher','-force_text_save'],wait_marker='[plugin] Camera_RegisterCommands',timeout=240);R.ready(True);execute(out,'reload');return verify(out)
if __name__=='__main__':raise SystemExit(main())
