import ast,hashlib,json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[3];out=pathlib.Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=True)
tree=ast.parse((ROOT/'test/modules/effect/test_array64_group_native.py').read_text(encoding='utf-8'));pieces={}
for node in tree.body:
    if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name) and node.targets[0].id in ['prefix','main']:
        pieces[node.targets[0].id]=ast.literal_eval(node.value)
source=(ROOT/'src/plugin/SDK_RVA/variable64/array64_existing_transaction.c').read_text(encoding='utf-8')
group=(ROOT/'src/plugin/SDK_RVA/variable64/array64_group_readonly.c').read_text(encoding='utf-8').replace('#include "native_array_readonly.c"',(ROOT/'src/plugin/SDK_RVA/variable64/native_array_readonly.c').read_text(encoding='utf-8'))
source=source.replace('#include "array64_group_readonly.c"',group)
helpers=pieces['main'].split('int main(void)')[0]
main=r'''
static int calls,reject_call,after_write,always_fail,persist_fail_from,foreign_change;
int tx_write_existing(void* c,const char* key,long long raw){unsigned h=hash(key),mask=*(unsigned*)((unsigned char*)c+36);unsigned char* p=nodes+(h&mask)*48;calls++;
 if(always_fail||(persist_fail_from&&calls>=persist_fail_from)||(calls==reject_call&&!after_write))return 0;
 for(int i=0;i<255;i++,p+=48){if(p[4]<=i)return 0;if(*(unsigned*)p==h&&!strcmp(nameat(p),key)){*(long long*)(p+40)=raw;if(foreign_change&&calls==2)keyput("demo","kind^1",500000);return calls!=reject_call;}}return 0;}
static void prepare(void){reset(255);make("demo",2);element("demo",0,1234567890112500LL,1);element("demo",1,-1,1);put("demo",100000);put("demo^num",200000);put("demo^0",250000);put("demo^1",775000);calls=reject_call=after_write=always_fail=persist_fail_from=foreign_change=0;}
int main(void){int i,j,s,n,g;long long raw;unsigned char* before=malloc(sizeof(nodes));
 prepare();s=Array64_SetExisting(header,"demo",0,2,LLONG_MIN,1,0,0);check("commit_min",s==1);test("committed_read","demo",0,1,LLONG_MIN,2,4,-1);test("other_element","demo",1,1,-1,2,4,-1);
 s=Array64_SetExisting(header,"demo",0,4,250000,0,0,0);check("demote_native",s==1);test("native_result","demo",0,1,250000,2,6,-1);
 for(i=1;i<=5;i++){prepare();memcpy(before,nodes,sizeof(nodes));s=Array64_SetExisting(header,"demo",0,2,LLONG_MAX,1,i,0);check("injected_stage_restored",s==2&&!memcmp(before,nodes,sizeof(nodes)));}
 for(i=1;i<=4;i++){prepare();s=Array64_SetExisting(header,"demo",0,2,LLONG_MAX,1,5,i);check("rollback_quarantine",s==-3);test("quarantine_refuses_read","demo",0,-5,123,-99,-99,-1);long long gen;check("odd_persisted",na_lookup(header,"__v64a_demo_gen",&gen)==1&&gen==300000);}
 for(i=1;i<=5;i++)for(j=0;j<=1;j++){prepare();memcpy(before,nodes,sizeof(nodes));reject_call=i;after_write=j;s=Array64_SetExisting(header,"demo",0,2,LLONG_MAX,1,0,0);check("backend_before_or_after_write_failure",s==2&&!memcmp(before,nodes,sizeof(nodes)));}
 prepare();memcpy(before,nodes,sizeof(nodes));s=Array64_SetExisting(header,"demo",0,0,LLONG_MAX,1,0,0);check("stale_no_write",s==-1&&!calls&&!memcmp(before,nodes,sizeof(nodes)));
 s=Array64_SetExisting(header,"demo",0,2,LLONG_MAX,0,0,0);check("unsafe_native_no_write",s==-1&&!calls&&!memcmp(before,nodes,sizeof(nodes)));
 s=Array64_SetExisting(header,"demo",2,2,1,1,0,0);check("index_no_write",s==-1&&!calls&&!memcmp(before,nodes,sizeof(nodes)));
 keyput("demo","gen",214748364600000LL);memcpy(before,nodes,sizeof(nodes));s=Array64_SetExisting(header,"demo",0,2147483646,1,1,0,0);check("generation_no_wrap",s==-1&&!calls&&!memcmp(before,nodes,sizeof(nodes)));
 prepare();always_fail=1;memcpy(before,nodes,sizeof(nodes));s=Array64_SetExisting(header,"demo",0,2,LLONG_MAX,1,0,0);check("initial_marker_backend_unavailable",s==2&&!memcmp(before,nodes,sizeof(nodes)));
 prepare();persist_fail_from=2;s=Array64_SetExisting(header,"demo",0,2,LLONG_MAX,1,0,0);check("persistent_backend_failure_explicit",s==-4);test("observed_odd_after_backend_failure","demo",0,-5,123,-99,-99,-1);
 prepare();foreign_change=1;s=Array64_SetExisting(header,"demo",0,2,LLONG_MAX,1,0,0);check("foreign_group_change_quarantined",s==-3);test("foreign_change_refuses_read","demo",0,-5,123,-99,-99,-1);
 prepare();int gen=2;for(i=0;i<512;i++){long long want=i%2?250000:LLONG_MIN;s=Array64_SetExisting(header,"demo",0,gen,want,i%2?0:1,0,0);gen+=2;check("alternating_setter",s==1);int q=Array64Group_Read(header,"demo",0,gen,&raw,&n,&g);check("alternating_read",q==1&&raw==want&&n==2&&g==gen);memcpy(before,nodes,sizeof(nodes));
 s=Array64_SetExisting(header,"demo",0,gen,LLONG_MAX,1,2+i%4,0);check("pressure_compensation",s==2&&!memcmp(before,nodes,sizeof(nodes)));}
 check("native_scalar_untouched",na_lookup(header,"demo",&raw)==1&&raw==100000);check("native_array_untouched",na_lookup(header,"demo^0",&raw)==1&&raw==250000&&na_lookup(header,"demo^1",&raw)==1&&raw==775000);
 free(before);printf("checks=%d passed=%d failed=%d\n",checks,checks-failed,failed);return failed?1:0;
}
'''
(out/'fixture.c').write_text(pieces['prefix']+source+helpers+main,encoding='ascii');vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
(out/'compile.cmd').write_text('@echo off\r\ncall "'+vc+'" >nul\r\ncl /nologo /W4 /TC fixture.c /Fe:fixture.exe >compile.stdout.txt 2>compile.stderr.txt\r\nexit /b %errorlevel%\r\n',encoding='ascii')
p=subprocess.run(['cmd.exe','/c',str(out/'compile.cmd')],cwd=out,capture_output=True)
if p.returncode:print((out/'compile.stdout.txt').read_bytes().decode('mbcs',errors='replace'));raise SystemExit(p.returncode)
p=subprocess.run([str(out/'fixture.exe')],capture_output=True);(out/'stdout.txt').write_bytes(p.stdout);(out/'stderr.txt').write_bytes(p.stderr)
r={'command':sys.argv,'expanded_sha256':hashlib.sha256(source.encode()).hexdigest(),'stdout':p.stdout.decode('ascii'),'stderr':p.stderr.decode('ascii'),'exit':p.returncode,'synthetic_memory_and_write_adapter':True}
(out/'result.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r,indent=2));raise SystemExit(p.returncode)
