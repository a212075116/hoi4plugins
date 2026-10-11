import sys,json,pathlib,time
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'test/lib'))
import frida_host as FH
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
js=(ROOT/'test/lib/exec_console_command.js').read_text(encoding='utf-8')+r'''
const samples=[];
const img=Process.getModuleByName('hoi4.exe').base;
const readParam=new NativeFunction(img.add(0x544C90),'void',['pointer','pointer','pointer','pointer','pointer']);
const containerFn=new NativeFunction(img.add(0x542500),'pointer',Array(10).fill('pointer'));
function lookup(container,name){
 let tbl=container.add(16),b=tbl.add(8).readPointer(),mask=tbl.add(20).readU32();
 let h=0x811c9dc5;for(let i=0;i<name.length;i++)h=Math.imul(h^name.charCodeAt(i),0x01000193)>>>0;
 let bucket=b.add(48*(h&mask)),count=bucket.add(4).readU8(),nodes=[];
 for(let i=0;i<Math.min(count,64);i++){let node=bucket.add(i*48);nodes.push({hash:node.readU32(),count:node.add(4).readU8(),name:rstr(node.add(8)),raw:node.add(40).readS64().toString()});}
 return {mask,count,nodes};
}
Interceptor.attach(img.add(0x34C760),{onEnter(args){
 const self=args[0],ctx=args[1],nm=self.add(200);
 const name=rstr(nm);
 if(!name.startsWith('st_') || samples.length>=6)return;
 const saved=nm.readByteArray(32),o=Memory.alloc(8),outputs=Memory.alloc(128);
 const values={};
 try{
  const container=containerFn(self.add(88),ctx,...Array.from({length:8},(_,i)=>outputs.add(i*8)));
  const lookupValues={};for(const s of [name,name+'_var64f',name+'_notthere'])lookupValues[s]=lookup(container,s);
  for(const s of [name,name+'_var64f',name+'_notthere']){
   wstr(nm,s);o.writeS64(-1);
   readParam(self.add(88),o,ctx,ptr(0),ptr(0));
   values[s]=o.readS64().toString();
  }
  samples.push({name,flags:self.add(96).readU32(),container:container.toString(),lookupValues,values});
 }catch(e){samples.push({name,error:String(e)});}
 finally{nm.writeByteArray(saved);}
}});
rpc.exports.readsamples=function(){return samples;};
'''
pid=FH.find_pid();session=__import__('frida').attach(pid);sc=session.create_script(js);sc.load()
try:
 print(sc.exports_sync.exec('event',['zzv64stress.3']),flush=True)
 time.sleep(2)
 result=sc.exports_sync.readsamples()
 print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
 (ROOT/'test/reports/20261012_variable64_transaction/stress/readonly_probe.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
finally:FH.detach(session)
