import json,pathlib,re,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'test/lib'))
import frida_host as FH
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
log=(ROOT.parent/'reports/mod_loader_tbb.log').read_text(encoding='utf-8')
ids=[int(re.findall(r'\[trg\] \+ '+name+r' tokenId=(\d+)',log)[-1]) for name in ['plugin_trigger_true','plugin_trigger_false','plugin_trigger_scope']]
js=(ROOT/'test/lib/exec_console_command.js').read_text(encoding='utf-8')+'\nconst customIds='+json.dumps(ids)+';\n'+r'''
const b=Process.getModuleByName('hoi4.exe').base;
const samples=[];let busy=false;
const freeGame=new NativeFunction(b.add(0x21c9b00),'void',['pointer']);
function entry(id){const m=b.add(0x3330050).readPointer(),h=m.add(24).readPointer();let n=h.add(8).readPointer();for(let i=0;i<4096;i++){if(n.isNull()||n.add(25).readU8())return null;let k=n.add(32).readS32();if(k===id)return n.add(40).readPointer();n=n.add(id<k?0:16).readPointer();}return null;}
Interceptor.attach(b.add(0x12cf2b0),{onEnter(args){
 if(busy||samples.length||args[1].readUtf8String(11)!=='tr_true_yes')return;
 busy=true;
 try{
  for(let id of customIds){
   const e=entry(id);if(!e){samples.push({id,error:'missing entry'});continue;}
   const make=new NativeFunction(e.readPointer().add(8).readPointer(),'pointer',[]);
   const self=make(),o=Memory.alloc(32);self.add(88).writeU8(1);
   const fn=new NativeFunction(self.readPointer().add(168).readPointer(),'pointer',['pointer','pointer','pointer','uchar','int']);
   fn(self,o,args[0],0,0);const text=rstr(o);samples.push({id,text});
   if(o.add(24).readU64().toNumber()>15)freeGame(o.readPointer());
   const destroy=new NativeFunction(self.readPointer().readPointer(),'pointer',['pointer','uint']);destroy(self,1);
  }
 }catch(e){samples.push({error:String(e)});}finally{busy=false;}
}});
rpc.exports.tooltips=function(){return samples;};
'''
import frida
session=frida.attach(FH.find_pid());sc=session.create_script(js);sc.load()
try:
 result=sc.exports_sync.exec('event',['zztriggerreg.1']);print(result,flush=True);time.sleep(2)
 samples=sc.exports_sync.tooltips();print(json.dumps(samples,ensure_ascii=False,indent=2))
 out=ROOT/'test/reports/20261012_variable64_transaction/trigger/tooltip.json'
 out.write_text(json.dumps(samples,ensure_ascii=False,indent=2),encoding='utf-8')
 expected=['Plugin true predicate = yes\n','Plugin false predicate = yes\n','Plugin scope predicate = yes\n']
 raise SystemExit(0 if [x.get('text') for x in samples]==expected else 1)
finally:FH.detach(session)
