import argparse,hashlib,inspect,json,pathlib,re,secrets,sys,time
import verify_array64_shape as S
D=S.D;T=S.T;R=S.R;ROOT=S.ROOT;TX=S.TX;SOURCE=ROOT/'src/plugin/SDK_RVA/variable64/array64_shape_journal.c'
CASES=['jcreate','jresize','jclear','jmismatch','jforeign','jretry']
PARAMS={name:([0,0,0,'-9223372036854775808',1,2] if name=='jcreate' else [4,0,2,'0',1,0] if name=='jclear' else [5,0,2,'250000',0,4]) for name in CASES}
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
def expanded():return SOURCE.read_text(encoding='utf-8').replace('#include "array64_shape_transaction.c"',S.expanded())
def fixtures():
    body=inspect.getsource(D.fixtures).replace('def fixtures():','def build():').replace("['persist','stale']",repr(CASES));ns=dict(vars(D));exec(body,ns);text,e=ns['build']();branch=[secrets.randbelow(2147483646)+1 for _ in range(4)]
    for row in e:row['stamps']=branch+[secrets.randbelow(2147483646)+1 for _ in range(4)];row['nonce']=[secrets.randbelow(2147483646)+1 for _ in range(4)]
    counters={};lines=[]
    for line in text.splitlines():
        m=re.search(r'var = (global\.)?(d[pqr])_(tx\w+)',line)
        if m:
            prefix=m.group(1) or '';phase=m.group(2);name=m.group(3);idx=counters.get(phase,0);row=e[idx];counters[phase]=idx+1
            if phase=='dp':
                if row['case']=='jcreate':
                    for suffix in ['lo','hi','kind']:lines.append('clear_array = '+prefix+'__v64a_'+name+'_'+suffix)
                    for suffix in ['ver','gen','len']:lines.append('clear_variable = '+prefix+'__v64a_'+name+'_'+suffix)
                else:
                    for i,v in enumerate(row['stamps']):lines.append('set_variable = { '+prefix+'__v64o_'+name+'_'+('b' if i<4 else 'i')+str(i%4)+' = '+str(v)+' }')
        lines.append(line)
    return '\n'.join(lines).replace('zzads','zzajr')+'\n',e
def probe(address,expected,records):
    js=S.probe(address,expected).replace('const source='+json.dumps(S.expanded()),'const source='+json.dumps(expanded()))
    js=js.replace("return data.some(root=>key===root||key.startsWith(root+'^'));","for(let i=0;i<5;i++)data.push('__v64t_'+name+'_'+(i<4?'n'+i:'p'));return data.some(root=>key===root||key.startsWith(root+'^'));")
    at=js.index('function capture(self,ctx)');end=js.index('rpc.exports.samples=()=>rows;',at)
    custom='const durableRecords='+json.dumps(records)+';\nconst journalParams='+json.dumps(PARAMS)+';\n'+r'''
const journalBytes=new NativeFunction(cm.Array64_JournalBytes,'uint',[])();
const prepareJournal=new NativeFunction(cm.Array64_JournalPrepare,'int',['pointer','pointer','pointer','uint64','int','int','int','int64','int','int','pointer','pointer','pointer','uint','pointer','pointer']);
const beginJournal=new NativeFunction(cm.Array64_JournalBegin,'int',['pointer','pointer','pointer','uint64','pointer','uint','pointer']);
const applyJournal=new NativeFunction(cm.Array64_JournalApply,'int',['pointer','pointer','pointer','uint64','pointer','uint','pointer','pointer','int','int']);
const recoverJournal=new NativeFunction(cm.Array64_JournalRecover,'int',['pointer','pointer','pointer','uint64','pointer','uint','pointer','int']);
const finishJournal=new NativeFunction(cm.Array64_JournalFinish,'int',['pointer','pointer','pointer','uint64','pointer','uint','pointer','int']);
const preparedJournal=new Map();
const fixturePut=new NativeFunction(putNew,'int',['pointer','pointer','int64']);
const fixtureErase=new NativeFunction(eraseKey,'int',['pointer','pointer']);
function input(hex){return blob(hex);}
function runRecover(c,name,scope,lineage,hex,fail=0){const b=input(hex),work=Memory.alloc(journalBytes);return recoverJournal(c,Memory.allocUtf8String(name),Memory.allocUtf8String(scope),lineage,b.p,b.bytes,work,fail);}
function capture(self,ctx){try{const d=self.add(88),n=txt(d.add(112));if(!/^(dp|dq|dr)_tx/.test(n))return;const name=n.slice(3),extra=Array.from({length:8},()=>Memory.alloc(8)),c=resolve(d,ctx,...extra),id=c.toString()+n;if(seen.has(id))return;seen.add(id);
 const sid=Number(slot(c,'ds_scopeid').readS64().toString())/100000,scope=scopes[sid-1],lineage=new UInt64(slot(c,'ds_lineage').readS64().toString()),row=expected.find(x=>x.scope===scope&&x.name===name),key=scope+'|'+name;
 if(!row)throw Error('case');const before=map(c),start=writes.length,steps=[];let record=null;
 if(n.startsWith('dp_')){
   const p=journalParams[row.case],stamps=Memory.alloc(32),nonce=Memory.alloc(16),buffer=Memory.alloc(100000),written=Memory.alloc(4);
   row.stamps.forEach((v,i)=>stamps.add(4*i).writeU32(v));row.nonce.forEach((v,i)=>nonce.add(4*i).writeU32(v));written.writeU32(0);
   const result=prepareJournal(c,Memory.allocUtf8String(name),Memory.allocUtf8String(scope),lineage,p[0],p[1],p[2],new Int64(p[3]),p[4],p[5],stamps,nonce,buffer,100000,written,Memory.alloc(journalBytes));
   if(result!==1)throw Error('journal prepare '+result);record={result,hex:bytes(buffer,written.readU32())};preparedJournal.set(key,record.hex);
 }else if(n.startsWith('dq_')){
   const b=input(preparedJournal.get(key)),j=Memory.alloc(journalBytes),work=Memory.alloc(workBytes);
   const begun=beginJournal(c,Memory.allocUtf8String(name),Memory.allocUtf8String(scope),lineage,b.p,b.bytes,j);steps.push({key:'begin',result:begun});
   const result=applyJournal(c,Memory.allocUtf8String(name),Memory.allocUtf8String(scope),lineage,b.p,b.bytes,j,work,14,row.case==='jclear'?1:12);steps.push({key:'isolate',result});
   // Simulate restart at genuine partial shapes: slots/length/ownership removed by native erase.
   const er=(suffix)=>fixtureErase(c,Memory.allocUtf8String(suffix));
   if(row.case==='jcreate'){fixturePut(c,Memory.allocUtf8String('__v64a_'+name+'_lo^1'),new Int64(0));}
   else if(row.case==='jclear'){er('__v64a_'+name+'_hi^0');er('__v64o_'+name+'_i0');er('__v64a_'+name+'_hi^num');}
   else {er('__v64a_'+name+'_lo^0');fixturePut(c,Memory.allocUtf8String('__v64a_'+name+'_hi^num'),new Int64(400000));}
   if(row.case==='jforeign')fixturePut(c,Memory.allocUtf8String('__v64o_'+name+'_i0'),new Int64((row.stamps[4]%2147483647+1)*100000));
 }else{
   const hex=durableRecords[key].record;
   if(row.case==='jmismatch'){
     const foreign=Object.entries(durableRecords).find(([k])=>k.endsWith('|'+name)&&k!==key)[1].record,beforeAttempt=canonical(map(c)),w=writes.length;
     steps.push({key:'mismatch',result:runRecover(c,name,scope,lineage,foreign),noWrite:beforeAttempt===canonical(map(c))&&writes.length===w});
   }else if(row.case==='jforeign'){
     const beforeAttempt=canonical(map(c)),w=writes.length;steps.push({key:'foreign',result:runRecover(c,name,scope,lineage,hex),noWrite:beforeAttempt===canonical(map(c))&&writes.length===w});
   }else{
     if(row.case==='jretry'){const result=runRecover(c,name,scope,lineage,hex,12);steps.push({key:'retry_failure',result,still:group(c,name)});}
     const result=runRecover(c,name,scope,lineage,hex);steps.push({key:'recover',result});
     const w=writes.length,beforeReplay=canonical(map(c));steps.push({key:'replay',result:runRecover(c,name,scope,lineage,hex),noWrite:w===writes.length&&beforeReplay===canonical(map(c))});
     const b=input(hex),j=Memory.alloc(journalBytes);steps.push({key:'finish_idempotent',result:finishJournal(c,Memory.allocUtf8String(name),Memory.allocUtf8String(scope),lineage,b.p,b.bytes,j,2)});
   }
 }
 const afterMap=map(c);rows.push({phase:n.slice(0,2),name,scope,container:c.toString(),record,old:null,steps,after:group(c,name),beforeMap:before,afterMap,unrelatedUnchanged:canonical(without(before,name))===canonical(without(afterMap,name)),sameMap:canonical(before)===canonical(afterMap),writes:writes.slice(start)});
}catch(e){rows.push({error:String(e)});}}
'''
    return js[:at]+custom+js[end:]
def execute(out,phase):
    import frida
    e=json.loads(R.read(out/'expected.json'));records=D.loaded_records(out) if phase=='reload' else {};addr=re.findall(r'\[trg\] \+ plugin_check_variable64.*eval=([0-9A-Fa-f]+)',R.read(pathlib.Path(R.HL.LOG)))[-1]
    (out/(phase+'_backend.c')).write_text(expanded(),encoding='utf-8');s=frida.attach(R.FH.find_pid());sc=s.create_script(probe(addr,e,records));commands=[];messages=[]
    sc.on('message',lambda message,data:messages.append(message))
    try:
        sc.load()
        try:sc.exports_sync.samples()
        except Exception:
            (out/(phase+'_startup_messages.json')).write_text(json.dumps(messages,indent=2),encoding='utf-8');raise
        for event in (['zzajr.1','zzajr.2'] if phase=='write' else ['zzajr.3']):
            text=sc.exports_sync.exec('event',[event]);print(text,flush=True);commands.append({'input':'event '+event,'stdout':text});assert 'out->ok     = 1' in text
            if event=='zzajr.1':D.persist(out,sc.exports_sync.samples());commands.append({'input':'flush/reopen intents before Begin and mutations','count':len(D.loaded_records(out))})
        (out/(phase+'_samples.json')).write_text(json.dumps(sc.exports_sync.samples(),indent=2),encoding='utf-8')
        if phase=='write':
            start=time.time();text=sc.exports_sync.exec('savegame',['ajr']);print(text,flush=True);commands.append({'input':'savegame ajr','stdout':text});assert 'out->ok     = 1' in text
            p=R.DOC/'save games/ajr.hoi4';end=time.time()+30
            while not p.exists() or p.stat().st_mtime<start:
                if time.time()>end:raise RuntimeError('fresh save missing')
                time.sleep(.2)
            (out/'save_snapshot.hoi4').write_bytes(p.read_bytes())
    finally:R.FH.detach(s)
    (out/(phase+'_commands.json')).write_text(json.dumps(commands,indent=2),encoding='utf-8')
    for p,n in [(R.DOC/'logs/game.log','game'),(R.DOC/'logs/error.log','error'),(pathlib.Path(R.HL.LOG),'plugin')]:
        if p.exists():(out/(phase+'_'+n+'.log')).write_bytes(p.read_bytes())
def verify(out):
    expected=json.loads(R.read(out/'expected.json'));rows=[]
    for phase in ['write','reload']:
        samples=json.loads(R.read(out/(phase+'_samples.json')));g=R.read(out/(phase+'_game.log'));selected=[x for x in samples if x.get('phase')==('dq' if phase=='write' else 'dr')]
        rows += [{'key':phase+'.source','ok':R.read(out/(phase+'_backend.c'))==expanded()},{'key':phase+'.captures','ok':len(samples)==(60 if phase=='write' else 30) and len(selected)==30 and not any('error' in x for x in samples)}]
        for e,s in zip(expected,selected):
            h=s.get('after',{}).get('head',{});ok=s.get('scope')==e['scope'] and s.get('unrelatedUnchanged')
            if phase=='write':ok=ok and h.get('status')==-5 and [v['result'] for v in s['steps'][:2]]==[1,-3]
            elif e['case'] in ['jmismatch','jforeign']:ok=ok and h.get('status')==-5 and s['sameMap'] and not s['writes']
            elif e['case']=='jcreate':ok=ok and h.get('status')==0 and not any(k.startswith('__v64a_'+e['name']+'_') or k.startswith('__v64o_'+e['name']+'_') or k.startswith('__v64t_'+e['name']+'_') for k in s['afterMap'])
            else:ok=ok and h.get('generation')==4 and [v['raw'] for v in s['after']['values']]==['1234567890112500','-1'] and not any(k.startswith('__v64t_'+e['name']+'_') for k in s['afterMap'])
            rows.append({'key':phase+'.'+e['label']+'.'+e['case'],'ok':bool(ok),'observed':s})
            for step in s['steps']:
                k=step['key'];want=-1 if k=='mismatch' else -7 if k=='foreign' else -3 if k in ['isolate','retry_failure'] else -5 if k=='replay' else 2 if k=='finish_idempotent' else 1
                good=step['result']==want and step.get('noWrite',True)
                if k=='retry_failure':good=good and step['still']['head']['status']==-5
                rows.append({'key':phase+'.'+e['label']+'.'+e['case']+'.'+k,'ok':good})
            m=re.findall(r'DS '+re.escape(e['label']+'.'+e['case'])+r' scalar=(\S+) a0=(\S+) a1=(\S+)',g);rows.append({'key':phase+'.'+e['label']+'.'+e['case']+'.native','ok':bool(m) and m[-1]==('12345678901.125','2.5','7.75')})
    rows.append({'key':'intent_reopen','ok':len(D.loaded_records(out))==30})
    for key,items in D.loaded_records(out).items():
        data=bytes.fromhex(items['record']);sl=int.from_bytes(data[104:108],'little');nl=int.from_bytes(data[108:112],'little');nested=int.from_bytes(data[112:116],'little')
        old=int.from_bytes(data[20:24],'little',signed=True);target=int.from_bytes(data[28:32],'little',signed=True);op=int.from_bytes(data[12:16],'little');h=14695981039346656037
        for value in data[:-8]:h=((h^value)*1099511628211)&((1<<64)-1)
        scope=data[120:120+sl].decode('ascii');name=data[120+sl:120+sl+nl].decode('ascii')
        good=data[:8]==b'A64JRN02' and int.from_bytes(data[8:12],'little')==1 and len(data)==128+sl+nl+nested and h==int.from_bytes(data[-8:],'little') and scope+'|'+name==key
        if op==0:good=good and old==-1 and target==2 and nested==0
        else:
            owned=data[120+sl+nl:-8];oh=14695981039346656037
            for value in owned[:-8]:oh=((oh^value)*1099511628211)&((1<<64)-1)
            decoded=D.inspect_record(owned[48:-8],key);good=good and old==2 and target==(-1 if op==4 else 4) and owned[:8]==b'A64OWN02' and oh==int.from_bytes(owned[-8:],'little') and decoded['generation']==2 and decoded['raws']==['1234567890112500','-1']
        rows.append({'key':'wire_oracle.'+key,'ok':bool(good)})
    errors=[l for phase in ['write','reload'] for l in R.read(out/(phase+'_error.log')).splitlines() if 'zz_array_journal' in l];rows.append({'key':'parser_errors','ok':not errors})
    r={'checks':len(rows),'passed':sum(v['ok'] for v in rows),'rows':rows,'errors':errors,'expanded_sha256':hashlib.sha256(expanded().encode()).hexdigest(),'alive':R.HL.proc_alive(),'public_api':False,'recovery':'matching five-word native transaction receipt; repairs only intent-authorized keys/range'};r['exit']=int(r['checks']!=r['passed'] or not r['alive']);(out/'comparison.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in r.items() if k!='rows'},indent=2));print('FAILED',json.dumps([v for v in rows if not v['ok']],indent=2));return r['exit']
def main():
    p=argparse.ArgumentParser();p.add_argument('phase');p.add_argument('--verify-only',action='store_true');a=p.parse_args();out=TX/'array_journal'/a.phase;out.mkdir(parents=True,exist_ok=True)
    if a.verify_only:return verify(out)
    if (out/'write_samples.json').exists():raise RuntimeError('preserve phase')
    text,e=fixtures();(out/'events.txt').write_text(text,encoding='utf-8');(out/'expected.json').write_text(json.dumps(e,indent=2),encoding='utf-8');(R.DOC/'mod/bakaifa/events/zz_array_journal.txt').write_text(text,encoding='utf-8')
    R.HL.launch(args=['-gdpr-compliant','-start_tag=ABY','-nolauncher','-force_text_save'],wait_marker='[plugin] Camera_RegisterCommands',timeout=240);R.ready();execute(out,'write')
    R.HL.launch(args=['-continuelastsave','-nolauncher','-force_text_save'],wait_marker='[plugin] Camera_RegisterCommands',timeout=240);R.ready(True);execute(out,'reload');return verify(out)
if __name__=='__main__':raise SystemExit(main())
