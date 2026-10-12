import argparse,hashlib,json,pathlib,re,sys
import verify_array64_transaction as T
R=T.R;ROOT=T.ROOT;TX=T.TX;SOURCE=ROOT/'src/plugin/SDK_RVA/variable64/array64_recovery.c'
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
def expanded():return SOURCE.read_text(encoding='utf-8').replace('#include "array64_existing_transaction.c"',T.expanded())
def fixtures():
    old=T.CASES;T.CASES=[{'name':n,'stage':5,'rollback':1,'wide':1,'raw':'9223372036854775807','want':1} for n in ['recover','retry','tamper','pressure']]
    try:text,e=T.fixtures()
    finally:T.CASES=old
    return text.replace('zzarraytx','zzarc').replace('at_marker','ac_marker').replace('AT WRITE DONE','AC WRITE DONE').replace('AT RELOAD DONE','AC RELOAD DONE'),e
def probe(address):
    js=T.probe(address).replace('const source='+json.dumps(T.expanded()),'const source='+json.dumps(expanded()))
    start=js.index('function capture(self,ctx)');end=js.index('rpc.exports.samples=()=>rows;',start)
    return js[:start]+r'''
const snapshotBytes=new NativeFunction(cm.Array64_SnapshotBytes,'uint',[])();
const captureSnapshot=new NativeFunction(cm.Array64_Capture,'int',['pointer','pointer','int','uint64','pointer']);
const recover=new NativeFunction(cm.Array64_Recover,'int',['pointer','pointer','uint64','pointer','int']);
const inspect=new NativeFunction(cm.Array64_InspectQuarantine,'int',['pointer','pointer','pointer','pointer']);
function doInspect(c,name){const n=Memory.alloc(4),g=Memory.alloc(4);n.writeS32(-99);g.writeS32(-99);const status=inspect(c,Memory.allocUtf8String(name),n,g);return{status,count:n.readS32(),generation:g.readS32()};}
function capture(self,ctx){try{const d=self.add(88),n=txt(d.add(112));if(!n.startsWith('at_tx')&&!n.startsWith('ar_tx'))return;
 const name=n.slice(3),extra=Array.from({length:8},()=>Memory.alloc(8)),c=resolve(d,ctx,...extra),id=c.toString()+n;if(seen.has(id))return;seen.add(id);
 const before=snap(c),protectedBefore=protectedSnap(c,name),baseline=group(c,name),start=writes.length,steps=[];
 if(n.startsWith('at_')){
   const owner=new UInt64(1000+rows.length),ptrname=Memory.allocUtf8String(name),saved=Memory.alloc(snapshotBytes);
   const captured=captureSnapshot(c,ptrname,2,owner,saved);steps.push({key:'capture',result:captured});if(captured!==1)throw Error('capture');
   if(name==='txpressure'){
     let gen=2;
     for(let round=0;round<16;round++){
       const stale=Memory.alloc(snapshotBytes);stale.writeByteArray(saved.readByteArray(snapshotBytes));
       const raw=round%2?'250000':'-9223372036854775808',wide=round%2?0:1;
       const commit=setGroup(c,ptrname,0,gen,new Int64(raw),wide,0,0);gen+=2;
       const cap=captureSnapshot(c,ptrname,gen,owner,saved);
       const failed=setGroup(c,ptrname,0,gen,new Int64('9223372036854775807'),1,5,1);
       const isolated=group(c,name),inspected=doInspect(c,name),oldBefore=snap(c),oldWrites=writes.length;
       const oldResult=recover(c,ptrname,owner,stale,0),staleNoWrite=oldBefore===snap(c)&&oldWrites===writes.length;
       const recovery=recover(c,ptrname,owner,saved,0);gen+=2;
       const readback=group(c,name),replayBefore=snap(c),replayWrites=writes.length;
       const replay=recover(c,ptrname,owner,saved,0),replayNoWrite=replayBefore===snap(c)&&replayWrites===writes.length;
       steps.push({key:'pressure',round,commit,cap,failed,isolated,inspected,oldResult,staleNoWrite,recovery,readback,replay,replayNoWrite,expectedRaw:raw,expectedGeneration:gen});
       if(round<15&&captureSnapshot(c,ptrname,gen,owner,saved)!==1)throw Error('next capture');
     }
   }else{
     const failed=setGroup(c,ptrname,0,2,new Int64('9223372036854775807'),1,5,1),isolated=group(c,name),inspection=doInspect(c,name);
     steps.push({key:'isolate',result:failed,isolated,inspection});
     if(name==='txtamper'){
       const bad=Memory.alloc(snapshotBytes);bad.writeByteArray(saved.readByteArray(snapshotBytes));bad.add(16).writeU8(bad.add(16).readU8()^1);
       for(const test of [{label:'checksum',container:c,owner,snapshot:bad},{label:'owner',container:c,owner:new UInt64(9999),snapshot:saved},{label:'container',container:c.add(8),owner,snapshot:saved}]){
         const bytesBefore=snap(c),writesBefore=writes.length,result=recover(test.container,ptrname,test.owner,test.snapshot,0);
         steps.push({key:test.label,result,noWrite:bytesBefore===snap(c)&&writesBefore===writes.length});
       }
     }
     if(name==='txretry'){
       const first=recover(c,ptrname,owner,saved,2),still=group(c,name);steps.push({key:'retry_failure',result:first,still});
     }
     const result=recover(c,ptrname,owner,saved,0),readback=group(c,name);steps.push({key:'recovery',result,readback});
     const replayBefore=snap(c),writesBefore=writes.length,replay=recover(c,ptrname,owner,saved,0);
     steps.push({key:'replay',result:replay,noWrite:replayBefore===snap(c)&&writesBefore===writes.length});
   }
 }
 rows.push({name,container:c.toString(),baseline,after:group(c,name),steps,onlyExpectedSlotsChanged:protectedBefore===protectedSnap(c,name),sameBytes:before===snap(c),writes:writes.slice(start)});
}catch(e){rows.push({error:String(e)});}}
''' + js[end:]
def verify(out):
    e=json.loads(R.read(out/'expected.json'));rows=[];ids={};pressure=0
    for phase in ['write','reload']:
        samples=json.loads(R.read(out/(phase+'_samples.json')));g=R.read(out/(phase+'_game.log'))
        rows.append({'key':phase+'.source','ok':R.read(out/(phase+'_backend.c'))==expanded()})
        rows.append({'key':phase+'.captures','ok':len(samples)==len(e) and not any('error' in s for s in samples),'count':len(samples)})
        ids[phase]=[s.get('container') for s in samples[::4]];rows.append({'key':phase+'.scopes','ok':len(set(ids[phase]))==5})
        for want,s in zip(e,samples):
            a=s.get('after',{});gen=66 if want['name']=='pressure' else 4;raw='250000' if gen==66 else '1234567890112500'
            good=s.get('name')==want['group'] and s.get('onlyExpectedSlotsChanged') and a.get('head',{}).get('generation')==gen and [v['raw'] for v in a.get('values',[])]==[raw,'-1'] and all(v['status']==1 for v in a.get('values',[]))
            if phase=='reload':good=good and s.get('sameBytes') and not s.get('writes')
            rows.append({'key':phase+'.'+want['label']+'.'+want['name']+'.restored','ok':bool(good),'observed':s})
            matches=re.findall(r'AT '+re.escape(want['label']+'.'+want['name'])+r' scalar=(\S+) a0=(\S+) a1=(\S+)',g)
            rows.append({'key':phase+'.'+want['label']+'.'+want['name']+'.native_untouched','ok':bool(matches) and matches[-1]==('12345678901.125','2.5','7.75')})
            if phase=='write':
                for step in s.get('steps',[]):
                    k=step['key'];ok=True
                    if k=='capture':ok=step['result']==1
                    elif k=='isolate':ok=step['result']==-3 and step['isolated']['head']['status']==-5 and step['inspection']=={'status':1,'count':2,'generation':3}
                    elif k in ['checksum','owner','container','replay']:ok=step['result']==-1 and step['noWrite']
                    elif k=='retry_failure':ok=step['result']==-3 and step['still']['head']['status']==-5
                    elif k=='recovery':ok=step['result']==1 and step['readback']['head']['generation']==4
                    elif k=='pressure':
                        pressure+=1;ok=step['commit']==step['cap']==step['recovery']==1 and step['failed']==-3 and step['isolated']['head']['status']==-5 and step['inspected']['status']==1 and step['oldResult']==-2 and step['staleNoWrite'] and step['replay']==-1 and step['replayNoWrite'] and step['readback']['head']['generation']==step['expectedGeneration'] and [v['raw'] for v in step['readback']['values']]==[step['expectedRaw'],'-1']
                    rows.append({'key':want['label']+'.'+want['name']+'.'+k+'.'+str(step.get('round','')),'ok':bool(ok)})
                rows.append({'key':want['label']+'.'+want['name']+'.adapter','ok':not any('error' in w for w in s.get('writes',[]))})
    errors=[l for phase in ['write','reload'] for l in R.read(out/(phase+'_error.log')).splitlines() if 'zz_array_recovery' in l]
    rows += [{'key':'marker','ok':'AT marker=20261012' in R.read(out/'reload_game.log')},{'key':'parser_errors','ok':not errors},{'key':'pressure_count','ok':pressure==80}]
    r={'checks':len(rows),'passed':sum(x['ok'] for x in rows),'rows':rows,'errors':errors,'identities':ids,'pressure_cycles':pressure,'expanded_sha256':hashlib.sha256(expanded().encode()).hexdigest(),'alive':R.HL.proc_alive(),'public_api':False};r['exit']=int(r['passed']!=r['checks'] or not r['alive'])
    (out/'comparison.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in r.items() if k!='rows'},indent=2));print('FAILED',json.dumps([v for v in rows if not v['ok']],indent=2));return r['exit']
def main():
    p=argparse.ArgumentParser();p.add_argument('phase');p.add_argument('--verify-only',action='store_true');a=p.parse_args();out=TX/'array_recovery'/a.phase;out.mkdir(parents=True,exist_ok=True)
    if a.verify_only:return verify(out)
    if (out/'write_samples.json').exists():raise RuntimeError('preserve phase')
    text,e=fixtures();(out/'events.txt').write_text(text,encoding='utf-8');(out/'expected.json').write_text(json.dumps(e,indent=2),encoding='utf-8');(R.DOC/'mod/bakaifa/events/zz_array_recovery.txt').write_text(text,encoding='utf-8')
    original_expanded=T.expanded;original_probe=T.probe
    # execute's globals are replaced only for this process; probe keeps the original builder.
    T.expanded=lambda:SOURCE.read_text(encoding='utf-8').replace('#include "array64_existing_transaction.c"',original_expanded())
    T.probe=lambda address:build_with_original(address,original_expanded,original_probe)
    R.HL.launch(args=['-gdpr-compliant','-start_tag=ABY','-nolauncher','-force_text_save'],wait_marker='[plugin] Camera_RegisterCommands',timeout=240);R.ready();T.execute(out,'write','zzarc.1',True)
    R.HL.launch(args=['-continuelastsave','-nolauncher','-force_text_save'],wait_marker='[plugin] Camera_RegisterCommands',timeout=240);R.ready(True);T.execute(out,'reload','zzarc.2')
    T.expanded=original_expanded;T.probe=original_probe
    return verify(out)
def build_with_original(address,old_expanded,old_probe):
    current_expanded=T.expanded;current_probe=T.probe;T.expanded=old_expanded;T.probe=old_probe
    try:return probe(address)
    finally:T.expanded=current_expanded;T.probe=current_probe
if __name__=='__main__':raise SystemExit(main())
