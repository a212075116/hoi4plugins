import ast,hashlib,json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[3];out=pathlib.Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=True)
def literal(file,name):
    for n in ast.parse(file.read_text(encoding='utf-8')).body:
        if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id==name:return ast.literal_eval(n.value)
    raise ValueError(name)
prefix=literal(ROOT/'test/modules/effect/test_array64_group_native.py','prefix');helpers=literal(ROOT/'test/modules/effect/test_array64_group_native.py','main').split('int main(void)')[0]+literal(ROOT/'test/modules/effect/test_array64_transaction_native.py','main').split('int main(void)')[0]+literal(ROOT/'test/modules/effect/test_array64_ownership_native.py','main').split('int main(void)')[0]
folder=(pathlib.Path(sys.argv[2]).resolve() if len(sys.argv)>2 else ROOT)/'src/plugin/SDK_RVA/variable64';source=(folder/'native_array_readonly.c').read_text(encoding='utf-8')
for name,previous in [('array64_group_readonly.c','native_array_readonly.c'),('array64_existing_transaction.c','array64_group_readonly.c'),('array64_recovery.c','array64_existing_transaction.c'),('array64_durable_snapshot.c','array64_recovery.c'),('array64_ownership_gate.c','array64_durable_snapshot.c'),('array64_shape_transaction.c','array64_ownership_gate.c')]:source=(folder/name).read_text(encoding='utf-8').replace('#include "'+previous+'"',source)
for header in ['array64_wire.h','array64_owner_key.h']:
    directive='#include "'+header+'"'
    if directive in source:source=source.replace(directive,(folder/header).read_text(encoding='utf-8').replace('#pragma once\n',''))
main=r'''
int as_native_put(void* c,const char* key,long long raw){(void)c;put(key,raw);return 1;}
int as_native_erase(void* c,const char* key){(void)c;unsigned h=hash(key),mask=*(unsigned*)(header+36);unsigned char* p=nodes+(h&mask)*48;
 for(int i=0;i<255;i++,p+=48){if(p[4]<=i)return 1;if(*(unsigned*)p==h&&!strcmp(nameat(p),key)){while(p[52]>1){memcpy(p,p+48,48);p[4]--;p+=48;}memset(p,0,48);return 1;}}return 0;}
static int mapsame(unsigned char* before){long long raw;int prior=0,current=0;for(int i=0;i<16384;i++){unsigned char* p=before+i*48;if(p[4]){prior++;if(na_lookup(header,nameat(p),&raw)!=1||raw!=*(long long*)(p+40))return 0;}if(nodes[i*48+4])current++;}return prior==current;}
int main(void){Array64ShapeWork* w=malloc(sizeof(*w));unsigned int stamps[8]={1,2,3,4,5,6,7,8};unsigned char* before=malloc(sizeof(nodes));int s,i,n,g;long long raw;
 reset(255);put("demo",250000);put("demo^num",100000);put("demo^0",775000);s=Array64_ShapeApply(header,"demo",0,0,0,LLONG_MIN,1,2,stamps,w,0,0);check("create",s==1);test("created","demo",1,1,LLONG_MIN,2,2,-1);check("same_scalar",na_lookup(header,"demo",&raw)==1&&raw==250000);
 s=Array64_ShapeApply(header,"demo",1,0,2,LLONG_MAX,1,0,0,w,0,0);check("append",s==1);test("appended","demo",2,1,LLONG_MAX,3,4,-1);
 s=Array64_ShapeApply(header,"demo",2,1,4,-1,1,0,0,w,0,0);check("insert",s==1);test("inserted","demo",1,1,-1,4,6,-1);test("shifted","demo",3,1,LLONG_MAX,4,6,-1);
 s=Array64_ShapeApply(header,"demo",3,0,6,0,1,0,0,w,0,0);check("erase",s==1);test("compressed","demo",0,1,-1,3,8,-1);
 s=Array64_ShapeApply(header,"demo",5,0,8,250000,0,5,0,w,0,0);check("grow",s==1);test("fill_native","demo",4,1,250000,5,10,-1);
 s=Array64_ShapeApply(header,"demo",5,0,10,0,1,0,0,w,0,0);check("shrink_zero",s==1);test("empty_retained","demo",0,2,123,0,12,-1);
 s=Array64_ShapeApply(header,"demo",4,0,12,0,1,0,0,w,0,0);check("destroy_clear",s==1);test("absent_after_clear","demo",0,0,123,-99,-99,-1);check("owner_removed",as_owner_absent(header,"demo"));check("plain_array_untouched",na_lookup(header,"demo^0",&raw)==1&&raw==775000);
 for(i=1;i<=24;i++){prepare();stamp("demo",200);memcpy(before,nodes,sizeof(nodes));s=Array64_ShapeApply(header,"demo",2,1,2,LLONG_MIN,1,0,0,w,i,0);check("insert_failure_exact_map",s==2&&mapsame(before));}
 for(i=1;i<=21;i++){prepare();stamp("demo",200);memcpy(before,nodes,sizeof(nodes));s=Array64_ShapeApply(header,"demo",4,0,2,0,1,0,0,w,i,0);check("clear_failure_exact_map",s==2&&mapsame(before));}
 for(i=1;i<=21;i++){reset(255);memcpy(before,nodes,sizeof(nodes));s=Array64_ShapeApply(header,"demo",0,0,0,LLONG_MIN,1,2,stamps,w,i,0);check("create_failure_exact_map",s==2&&mapsame(before));}
 prepare();stamp("demo",200);s=Array64_ShapeApply(header,"demo",2,1,2,LLONG_MIN,1,0,0,w,14,12);check("shape_quarantine",s==-3);test("read_refuses_partial","demo",0,-5,123,-99,-99,-1);
 reset(255);s=Array64_ShapeApply(header,"demo",0,0,0,LLONG_MIN,1,2,stamps,w,14,1);check("create_failure_quarantine",s==-3);test("new_tombstone","demo",0,-5,123,-99,-99,-1);
 reset(255);keyput("demo","lo^4095",900000);memcpy(before,nodes,sizeof(nodes));s=Array64_ShapeApply(header,"demo",0,0,0,0,1,0,stamps,w,0,0);check("collision_no_write",s==-2&&mapsame(before));
 reset(255);put("__v64o_demo_i0^0",100000);memcpy(before,nodes,sizeof(nodes));s=Array64_ShapeApply(header,"demo",0,0,0,0,1,0,stamps,w,0,0);check("owner_descendant_collision",s==-2&&mapsame(before));
 prepare();stamp("demo",200);memcpy(before,nodes,sizeof(nodes));check("stale_no_write",Array64_ShapeApply(header,"demo",1,0,0,0,1,0,0,w,0,0)==-2&&mapsame(before));check("bad_index_no_write",Array64_ShapeApply(header,"demo",2,-1,2,0,1,0,0,w,0,0)==-1&&mapsame(before));
 prepare();stamp("demo",200);g=2;for(i=0;i<64;i++){check("pressure_append",Array64_ShapeApply(header,"demo",1,0,g,LLONG_MIN,1,0,0,w,0,0)==1);g+=2;check("pressure_erase",Array64_ShapeApply(header,"demo",3,2,g,0,1,0,0,w,0,0)==1);g+=2;check("pressure_original",Array64Group_Read(header,"demo",0,g,&raw,&n,&s)==1&&raw==1234567890112500LL&&n==2);}
 reset(16383);s=Array64_ShapeApply(header,"abcdefghijklmnopqrst",0,0,0,-1,1,4096,stamps,w,0,0);check("4096_create",s==1);test("4096_read","abcdefghijklmnopqrst",4095,1,-1,4096,2,-1);memcpy(before,nodes,sizeof(nodes));check("4096_append_reject",Array64_ShapeApply(header,"abcdefghijklmnopqrst",1,0,2,0,1,0,0,w,0,0)==-1&&mapsame(before));
 free(w);free(before);printf("checks=%d passed=%d failed=%d\n",checks,checks-failed,failed);return failed?1:0;
}
'''
(out/'fixture.c').write_text(prefix+source+helpers+main,encoding='ascii');vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
(out/'compile.cmd').write_text('@echo off\r\ncall "'+vc+'" >nul\r\ncl /nologo /W4 /TC fixture.c /Fe:fixture.exe >compile.stdout.txt 2>compile.stderr.txt\r\nexit /b %errorlevel%\r\n',encoding='ascii')
p=subprocess.run(['cmd.exe','/c',str(out/'compile.cmd')],cwd=out,capture_output=True)
if p.returncode:print((out/'compile.stdout.txt').read_bytes().decode('mbcs',errors='replace'));raise SystemExit(p.returncode)
p=subprocess.run([str(out/'fixture.exe')],capture_output=True);(out/'stdout.txt').write_bytes(p.stdout);(out/'stderr.txt').write_bytes(p.stderr)
r={'command':sys.argv,'expanded_sha256':hashlib.sha256(source.encode()).hexdigest(),'stdout':p.stdout.decode('ascii'),'stderr':p.stderr.decode('ascii'),'exit':p.returncode,'synthetic_memory_and_write_adapter':True};(out/'result.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r,indent=2));raise SystemExit(p.returncode)
