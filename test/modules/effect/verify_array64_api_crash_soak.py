import argparse,ctypes,hashlib,json,pathlib,queue,re,subprocess,sys,threading,time
import verify_array64_api_lifecycle as L
P=L.P;R=L.R;ROOT=L.ROOT;TX=L.TX
sys.stdout.reconfigure(encoding='utf-8',errors='replace')

def fixture():
    check=[];soak=[]
    for label,scope,p in L.SCOPES:
        b=['recover_array64 = { var = '+p+'prf value = 0 }','log = "KS '+label+'.recover status=[?'+p+'__v64sys_status]"']
        for tag,index,value in [('value','0','12345678901.125'),('count','num',1)]:
            b+=['set_variable = { ks_ok = 0 }','if = { limit = { check_array64 = { var = '+p+'prf^'+index+' value = '+str(value)+' compare = equals } } set_variable = { ks_ok = 1 } }','log = "KS '+label+'.'+tag+' ok=[?ks_ok]"']
        check+=P.wrap(scope,b);b=[]
        for _ in range(4):
            b+=['append_array64 = { var = '+p+'prf value = -0.00001 }','insert_array64 = { var = '+p+'prf^0 value = -0.00001 }','set_array_element_native = { var = '+p+'prf^1 value = 2.5 }','set_array_element64 = { var = '+p+'prf^1 value = 12345678901.125 }','erase_array64 = { var = '+p+'prf^0 value = 0 }','erase_array64 = { var = '+p+'prf^1 value = 0 }']
        b+=['set_variable = { ks_ok = 0 }','if = { limit = { check_array64 = { var = '+p+'prf^0 value = 12345678901.125 compare = equals } check_array64 = { var = '+p+'prf^num value = 1 compare = equals } } set_variable = { ks_ok = 1 } }','log = "KS '+label+'.soak ok=[?ks_ok]"'];soak+=P.wrap(scope,b)
    def e(n,b):return 'country_event = { id = zzkill64.'+str(n)+' hidden = yes is_triggered_only = yes immediate = {\n'+'\n'.join(b)+'\n} option = { name = zzkill64.a } }\n'
    return 'add_namespace = zzkill64\n'+e(1,['append_array64 = { var = prf value = -0.00001 }'])+e(2,check)+e(3,soak)

def run(out,label,n,save=None):
    import frida
    s=frida.attach(R.FH.find_pid());sc=s.create_script((ROOT/'test/lib/exec_console_command.js').read_text(encoding='utf-8'));cmd=[]
    sources=[(R.DOC/'logs/game.log','game'),(pathlib.Path(R.HL.LOG),'plugin')];before={p:p.read_bytes() for p,_ in sources}
    try:
        sc.load();x=sc.exports_sync.exec('event',['zzkill64.'+str(n)]);cmd.append({'input':'event zzkill64.'+str(n),'stdout':x});assert 'out->ok     = 1' in x
        if save:
            start=time.time();x=sc.exports_sync.exec('savegame',[save]);cmd.append({'input':'savegame '+save,'stdout':x});assert 'out->ok     = 1' in x
            p=R.DOC/('save games/'+save+'.hoi4');end=time.time()+40
            while not p.exists() or p.stat().st_mtime<start:
                if time.time()>end:raise RuntimeError('fresh save missing')
                time.sleep(.2)
            (out/(label+'_save.hoi4')).write_bytes(p.read_bytes())
    finally:R.FH.detach(s)
    for p,name in sources:
        data=p.read_bytes();assert data.startswith(before[p]);(out/(label+'_'+name+'.log')).write_bytes(data[len(before[p]):])
    (out/(label+'_error.log')).write_bytes((R.DOC/'logs/error.log').read_bytes());(out/(label+'_commands.json')).write_text(json.dumps(cmd,ensure_ascii=False,indent=2),encoding='utf-8')

GATE=r'''
const base=Process.getModuleByName('hoi4.exe').base;let c=null,fired=false;const handles=new Map();
function std(p){const n=p.add(16).readU64().toNumber(),cap=p.add(24).readU64().toNumber();return(cap<=15?p:p.readPointer()).readUtf8String(n);}
function slot(name){if(!c)return null;let h=2166136261;for(const ch of name)h=Math.imul(h^ch.charCodeAt(0),16777619)>>>0;
 const b=c.add(24).readPointer(),mask=c.add(36).readU32();for(let i=0;i<255;i++){const p=b.add(48*((h&mask)+i));if(p.add(4).readU8()<=i)return null;if(p.readU32()===h&&std(p.add(8))===name)return p.add(40).readS64().toString();}throw Error('spill');}
function gate(extra){if(fired)return;fired=true;const native={};for(const key of ['__v64a_prf_gen','__v64a_prf_len','__v64a_prf_lo^1','__v64t_prf_n0','__v64t_prf_p'])native[key]=slot(key);
 send({kind:'gate',mode:MODE,container:c?c.toString():null,native,...extra});recv('release').wait();}
Interceptor.attach(base.add(0x542500),{onEnter(a){try{this.target=std(a[0].add(112))==='prf';}catch(e){this.target=false;}},onLeave(ret){if(this.target)c=ptr(ret.toString());}});
if(MODE==='temp_written'){
 Interceptor.attach(Process.getModuleByName('KERNELBASE.dll').getExportByName('CreateFileA'),{onEnter(a){this.path=a[0].readCString();},onLeave(ret){if(this.path.includes('/prf.a64j.')&&this.path.endsWith('.tmp'))handles.set(ret.toString(),this.path);}});
 Interceptor.attach(Process.getModuleByName('KERNELBASE.dll').getExportByName('WriteFile'),{onEnter(a){this.path=handles.get(a[0].toString());this.bytes=a[2].toUInt32();},onLeave(ret){if(this.path&&!ret.isNull())gate({temp_path:this.path,requested_bytes:this.bytes});}});
}else{
 Interceptor.attach(base.add(0xBC5C10),{onEnter(a){const v=a[1],name=v.readPointer().readUtf8String(v.add(8).readU64().toNumber());
  if((MODE==='before_receipt'&&name==='__v64t_prf_n0')||(MODE==='partial_element'&&name==='__v64a_prf_hi^1')){c=ptr(a[0].toString());gate({key:name});}}});
}
'''

def crash(out,mode,path,original):
    import frida
    pid=R.FH.find_pid();s=frida.attach(pid);source=(ROOT/'test/lib/exec_console_command.js').read_text(encoding='utf-8')+'\nconst MODE='+json.dumps(mode)+';\n'+GATE
    sc=s.create_script(source);q=queue.Queue();messages=[];result={}
    def message(m,data):
        messages.append(m)
        if m.get('type')=='send' and m['payload'].get('kind')=='gate':q.put(m['payload'])
        elif m.get('type')=='error':q.put({'script_error':m})
    sc.on('message',message);sc.load()
    def command():
        try:result['stdout']=sc.exports_sync.exec('event',['zzkill64.1'])
        except Exception as e:result['exception']=type(e).__name__+': '+str(e)
    thread=threading.Thread(target=command,daemon=True);thread.start()
    try:
        gate=q.get(timeout=45);assert 'script_error' not in gate,gate
    except Exception:
        (out/(mode+'_gate_error.json')).write_text(json.dumps({'messages':messages,'command':result},ensure_ascii=False,indent=2),encoding='utf-8');raise
    current=path.read_bytes();(out/(mode+'_sidecar.a64j')).write_bytes(current)
    before=hashlib.sha256(original).hexdigest();after=hashlib.sha256(current).hexdigest();temporary=None
    if 'temp_path' in gate:
        temp=pathlib.Path(gate['temp_path']);assert temp.resolve().parent==path.resolve().parent and temp.name.startswith(path.name+'.'+str(pid)+'.') and temp.name.endswith('.tmp')
        temporary={'path':str(temp),'bytes':temp.stat().st_size}
    kernel=ctypes.WinDLL('kernel32',use_last_error=True);kernel.OpenProcess.restype=ctypes.c_void_p;kernel.OpenProcess.argtypes=[ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong]
    kernel.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_ulong];kernel.GetExitCodeProcess.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)];kernel.CloseHandle.argtypes=[ctypes.c_void_p]
    handle=kernel.OpenProcess(0x101000,0,pid);assert handle
    proc=subprocess.run(['taskkill','/F','/PID',str(pid)],capture_output=True);code=ctypes.c_ulong()
    try:wait=kernel.WaitForSingleObject(handle,20000);assert kernel.GetExitCodeProcess(handle,ctypes.byref(code))
    finally:kernel.CloseHandle(handle)
    dead=wait==0 and code.value!=259;host_cleanup=False;thread.join(1)
    preliminary={'pid':pid,'gate':gate,'kill_exit':proc.returncode,'kill_stdout':proc.stdout.decode('mbcs',errors='replace'),'kill_stderr':proc.stderr.decode('mbcs',errors='replace'),'os_wait_status':wait,'os_process_exit_code':code.value,'process_dead':dead,'rpc_waiting':thread.is_alive()}
    (out/(mode+'_kill_observation.json')).write_text(json.dumps(preliminary,ensure_ascii=False,indent=2),encoding='utf-8')
    assert proc.returncode==0 and dead,preliminary
    if thread.is_alive():
        # Frida 17.23 sync RPC does not wake reliably from a gated process death.
        # Only notify the host request after independent Windows death confirmation.
        sc._on_destroyed();host_cleanup=True;thread.join(5)
    assert not thread.is_alive()
    if temporary:
        data=pathlib.Path(temporary['path']).read_bytes();(out/(mode+'_orphan.tmp')).write_bytes(data);temporary['sha256']=hashlib.sha256(data).hexdigest()
    evidence={'pid':pid,'gate':gate,'kill_command':proc.args,'kill_stdout':proc.stdout.decode('mbcs',errors='replace'),'kill_stderr':proc.stderr.decode('mbcs',errors='replace'),'kill_exit':proc.returncode,'os_wait_status':wait,'os_process_exit_code':code.value,'native_command':{'input':'event zzkill64.1',**result},'host_rpc_destroy_notification_after_confirmed_death':host_cleanup,'exception_is_not_native_crash_diagnostic':True,'original_sha256':before,'at_gate_sha256':after,'temporary':temporary,'messages':messages,'process_dead':dead}
    (out/(mode+'_crash.json')).write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
    for src,name in [(R.DOC/'logs/game.log','game'),(pathlib.Path(R.HL.LOG),'plugin')]: (out/(mode+'_killed_'+name+'.log')).write_bytes(src.read_bytes())
    print('REAL_KILL',mode,'PID',pid,'native',gate['native'],flush=True);return evidence

def memory(pid):
    class PMC(ctypes.Structure):
        _fields_=[('cb',ctypes.c_ulong),('faults',ctypes.c_ulong)]+[(k,ctypes.c_size_t) for k in ['peak_rss','rss','peak_paged','paged','peak_nonpaged','nonpaged','pagefile','peak_pagefile','private']]
    k=ctypes.WinDLL('kernel32',use_last_error=True);p=ctypes.WinDLL('psapi',use_last_error=True)
    k.OpenProcess.restype=ctypes.c_void_p;k.OpenProcess.argtypes=[ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong];k.CloseHandle.argtypes=[ctypes.c_void_p]
    p.GetProcessMemoryInfo.argtypes=[ctypes.c_void_p,ctypes.POINTER(PMC),ctypes.c_ulong];k.GetProcessHandleCount.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)]
    handle=k.OpenProcess(0x410,0,pid);assert handle;info=PMC();info.cb=ctypes.sizeof(info);count=ctypes.c_ulong()
    try:assert p.GetProcessMemoryInfo(handle,ctypes.byref(info),info.cb) and k.GetProcessHandleCount(handle,ctypes.byref(count));return {'time':time.time(),'rss':info.rss,'private':info.private,'handles':count.value}
    finally:k.CloseHandle(handle)

def verify(out):
    rows=[];config=json.loads((out/'config.json').read_text(encoding='utf-8')) if (out/'config.json').exists() else {'soak_only':False};modes=[] if config['soak_only'] else ['temp_written','before_receipt','partial_element']
    def check(label,text,country_status='0'):
        values=dict(re.findall(r'KS (\S+) ok=(\d+)',text));statuses=dict(re.findall(r'KS (\S+)\.recover status=(-?\d+)',text))
        for scope,_,_ in L.SCOPES:
            for key in ['value','count']:rows.append({'phase':label,'key':scope+'.'+key,'ok':values.get(scope+'.'+key)=='1'})
            want=country_status if scope=='country' else '0';rows.append({'phase':label,'key':scope+'.status','observed':statuses.get(scope),'want':want,'ok':statuses.get(scope)==want})
    check('baseline',R.read(out/'baseline_game.log'))
    for mode in modes:
        d=json.loads((out/(mode+'_crash.json')).read_text(encoding='utf-8'));n=d['gate']['native']
        rows+=[{'key':mode+'.actual_process_terminated','ok':d['kill_exit']==0 and d['process_dead']},{'key':mode+'.blocked_command_not_success','ok':'exception' in d['native_command'] and 'stdout' not in d['native_command']},{'key':mode+'.sidecar_transition','ok':(d['original_sha256']==d['at_gate_sha256'])==(mode=='temp_written')}]
        rows.append({'key':mode+'.native_checkpoint','ok':n['__v64a_prf_gen']==('700000' if mode=='partial_element' else '600000')})
        if mode=='partial_element':rows.append({'key':'partial_element.actual_partial_insert','ok':n['__v64a_prf_lo^1']=='-100000' and n['__v64t_prf_p']=='100000'})
        if mode=='temp_written':rows.append({'key':'temp_written.orphan_retained','ok':d['temporary']['bytes']>0})
        check(mode,R.read(out/(mode+'_restart_game.log')),'0' if mode=='temp_written' else '-5');check(mode+'.paired',R.read(out/(mode+'_paired_game.log')))
    soak=json.loads((out/'soak.json').read_text(encoding='utf-8'));logs=R.read(out/'soak_plugin.log');ops=re.findall(r'\[array64\] (\w+) name=prf status=(-?\d+)',logs)
    rows.append({'key':'soak.duration','seconds':soak['elapsed_seconds'],'ok':soak['elapsed_seconds']>=soak['requested_seconds']})
    rows.append({'key':'soak.all_operations','operations':len(ops),'ok':len(ops)==soak['batches']*120 and all(code=='0' for _,code in ops)})
    values=re.findall(r'KS (\S+)\.soak ok=(\d+)',R.read(out/'soak_game.log'));rows.append({'key':'soak.all_batch_values','ok':len(values)==soak['batches']*5 and all(v=='1' for _,v in values)})
    check('soak_reload',R.read(out/'soak_reload_game.log'))
    errors=[x for phase in ['baseline','soak_reload']+[m+'_restart' for m in modes]+[m+'_paired' for m in modes] for x in R.read(out/(phase+'_error.log')).splitlines() if 'zz_array64_api_crash_soak' in x]
    result={'checks':len(rows),'passed':sum(r['ok'] for r in rows),'rows':rows,'fixture_errors':errors,'alive':R.HL.proc_alive(),'dll_sha256':hashlib.sha256((ROOT.parent/'hoi4_mod_plugin.dll').read_bytes()).hexdigest(),'actual_forced_terminations':len(modes),'instrumented_gates':bool(modes),'soak':soak,'power_loss_verified':False,'multi_hour_soak_verified':False}
    result['resource_acceptance_complete']=False
    result['resource_delta']={k:soak['samples'][-1][k]-soak['samples'][0][k] for k in ['rss','private','handles']}
    if (out/'idle_control.json').exists():result['idle_control']=json.loads((out/'idle_control.json').read_text(encoding='utf-8'))
    result['exit']=int(result['checks']!=result['passed'] or bool(errors) or not result['alive']);(out/'comparison.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print('RESULT',result['passed'],'/',result['checks'],'exit',result['exit'],flush=True);return result['exit']

def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase');parser.add_argument('--seconds',type=int,default=180);parser.add_argument('--verify-only',action='store_true');parser.add_argument('--soak-only',action='store_true');args=parser.parse_args();out=TX/'api'/args.phase
    if args.verify_only:return verify(out)
    if out.exists():raise RuntimeError('preserve existing phase')
    assert args.seconds>=60;out.mkdir(parents=True);(out/'config.json').write_text(json.dumps({'soak_only':args.soak_only,'seconds':args.seconds},indent=2),encoding='utf-8');records=json.loads((TX/'api/lifecycle_v1/records.json').read_text(encoding='utf-8'));path=pathlib.Path(records['country']['path']);original=path.read_bytes()
    (out/'original_country.a64j').write_bytes(original);text=fixture();(out/'events.txt').write_text(text,encoding='utf-8');(R.DOC/'mod/bakaifa/events/zz_array64_api_crash_soak.txt').write_text(text,encoding='utf-8')
    P.launch(True);run(out,'baseline',2,'a64kill')
    for mode in ([] if args.soak_only else ['temp_written','before_receipt','partial_element']):
        assert path.read_bytes()==original;crash(out,mode,path,original);P.launch(True);run(out,mode+'_restart',2)
        path.write_bytes(original);run(out,mode+'_paired',2)
    pid=R.FH.find_pid();start=time.monotonic();samples=[memory(pid)];commands=[];batches=0;sources=[(R.DOC/'logs/game.log','game'),(pathlib.Path(R.HL.LOG),'plugin')];before={p:p.read_bytes() for p,_ in sources}
    import frida
    session=frida.attach(pid);sc=session.create_script((ROOT/'test/lib/exec_console_command.js').read_text(encoding='utf-8'))
    try:
        sc.load()
        while time.monotonic()-start<args.seconds:
            x=sc.exports_sync.exec('event',['zzkill64.3']);assert 'out->ok     = 1' in x;commands.append({'input':'event zzkill64.3','stdout':x});batches+=1
            if batches%10==0:samples.append(memory(pid));print('SOAK',batches,'batches',round(time.monotonic()-start,1),'seconds',flush=True)
            time.sleep(.5)
    finally:R.FH.detach(session)
    samples.append(memory(pid));elapsed=time.monotonic()-start
    for p,name in sources:(out/('soak_'+name+'.log')).write_bytes(p.read_bytes()[len(before[p]):])
    (out/'soak_commands.json').write_text(json.dumps(commands,ensure_ascii=False,indent=2),encoding='utf-8');(out/'soak.json').write_text(json.dumps({'requested_seconds':args.seconds,'elapsed_seconds':elapsed,'batches':batches,'operations':batches*120,'samples':samples,'not_leak_proof':True},indent=2),encoding='utf-8')
    run(out,'soak_save',2,'a64soak')
    (out/'soak_paired_sidecars').mkdir()
    paired={}
    for label,x in records.items():
        data=pathlib.Path(x['path']).read_bytes();(out/'soak_paired_sidecars'/(label+'.a64j')).write_bytes(data);paired[label]=hashlib.sha256(data).hexdigest()
    (out/'soak_paired_hashes.json').write_text(json.dumps(paired,indent=2),encoding='utf-8');P.launch(True);run(out,'soak_reload',2)
    # Preserve only this run's orphan before removing its exact verified path.
    if not args.soak_only:
        d=json.loads((out/'temp_written_crash.json').read_text(encoding='utf-8'));temp=pathlib.Path(d['temporary']['path']);assert temp.resolve().parent==path.resolve().parent and hashlib.sha256(temp.read_bytes()).hexdigest()==d['temporary']['sha256'];temp.unlink()
        (out/'orphan_cleanup.json').write_text(json.dumps({'path':str(temp),'retained_copy':str(out/'temp_written_orphan.tmp'),'sha256':d['temporary']['sha256'],'removed':not temp.exists()},indent=2),encoding='utf-8')
    return verify(out)

if __name__=='__main__':raise SystemExit(main())
