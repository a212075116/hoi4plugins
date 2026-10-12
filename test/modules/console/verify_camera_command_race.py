import json,pathlib,sys,time,frida
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import verify_external_console as V
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
label=sys.argv[1];out=V.OUT/(label+'_camera_race.json');assert not out.exists()
native='--native' in sys.argv
js=V.JS
if native:js+='\nconst nativeStats=rpc.exports;\n'+(V.ROOT/'test/lib/exec_console_command.js').read_text(encoding='utf-8')+'\nrpc.exports.snapshot=nativeStats.snapshot;\n'
p=V.pid();s=frida.attach(p);sc=s.create_script(js);sc.load();initial=sc.exports_sync.snapshot();records=[];rows=[]
def command(line):
 if not native:return V.command(p,line)
 words=line.split();text=sc.exports_sync.exec(words[0],words[1:]);return {'input':line,'executor':'native diagnostic RPC','stdout':text,'stderr':'','exit':int('out->ok     = 1' not in text)}
try:
 for i in range(3):
  records.append(command('setcamheight 500'));time.sleep(1)
  records.append(command('setcamheight 500'));records.append(command('event zzc.1'))
  time.sleep(1);x=sc.exports_sync.snapshot();rows.append({'case':i,'height':x['height'],'expected':950.25,'ok':abs(x['height']-950.25)<.1})
 records.append(command('setcamheight '+str(initial['height'])));time.sleep(1)
finally:s.detach()
r={'commands_success':all(x['exit']==0 for x in records),'rows':rows,'records':records,'checks':len(rows),'passed':sum(x['ok'] for x in rows)};r['exit']=int(r['passed']!=r['checks'] or not r['commands_success']);out.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(r,ensure_ascii=False,indent=2));raise SystemExit(r['exit'])
