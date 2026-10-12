import ast,hashlib,json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[3];out=pathlib.Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=True)
def literal(file,name):
    for n in ast.parse(file.read_text(encoding='utf-8')).body:
        if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id==name:return ast.literal_eval(n.value)
    raise ValueError(name)
prefix=literal(ROOT/'test/modules/effect/test_array64_group_native.py','prefix');helpers=literal(ROOT/'test/modules/effect/test_array64_group_native.py','main').split('int main(void)')[0]+literal(ROOT/'test/modules/effect/test_array64_transaction_native.py','main').split('int main(void)')[0]
folder=ROOT/'src/plugin/SDK_RVA/variable64';source=(folder/'native_array_readonly.c').read_text(encoding='utf-8')
for name,previous in [('array64_group_readonly.c','native_array_readonly.c'),('array64_existing_transaction.c','array64_group_readonly.c'),('array64_recovery.c','array64_existing_transaction.c'),('array64_durable_snapshot.c','array64_recovery.c'),('array64_ownership_gate.c','array64_durable_snapshot.c')]:source=(folder/name).read_text(encoding='utf-8').replace('#include "'+previous+'"',source)
main=r'''
static void stamp(const char* name,unsigned birth){char key[40];for(int i=0;i<8;i++){sprintf_s(key,40,"__v64o_%s_%c%d",name,i<4?'b':'i',i%4);put(key,(i<4?123+i:birth+i)*100000LL);}}
int main(void){Array64Snapshot* s=malloc(sizeof(*s)),*loaded=malloc(sizeof(*s));unsigned char* record=malloc(100000),*bad=malloc(100000),*before=malloc(sizeof(nodes));unsigned int bytes;int i;
 prepare();stamp("demo",200);Array64_Capture(header,"demo",2,42,s);check("owned_export",Array64_ExportOwned(s,"country:ABY",123,record,100000,&bytes)==1);check("wrapper_header",ad_get(record,8)==0x32304e574f343641ull&&bytes==167&&ad_get(record+12,4)==111);
 Array64_SetExisting(header,"demo",0,2,LLONG_MAX,1,5,1);calls=0;memcpy(before,nodes,sizeof(nodes));
 check("missing_file",Array64_ImportOwned(header,"demo","country:ABY",123,77,0,0,loaded)==-10);
 check("legacy_no_fallback",Array64_ImportOwned(header,"demo","country:ABY",123,77,record+48,bytes-56,loaded)==-11);
 memcpy(bad,record,bytes);bad[bytes-1]^=1;check("corrupt_wrapper",Array64_ImportOwned(header,"demo","country:ABY",123,77,bad,bytes,loaded)==-12);
 check("reject_no_write",!calls&&!memcmp(before,nodes,sizeof(nodes)));
 put("__v64o_demo_b0",99900000);calls=0;memcpy(before,nodes,sizeof(nodes));check("foreign_branch",Array64_ImportOwned(header,"demo","country:ABY",123,77,record,bytes,loaded)==-14);check("branch_no_write",!calls&&!memcmp(before,nodes,sizeof(nodes)));
 stamp("demo",300);check("new_incarnation_same_gen",Array64_ImportOwned(header,"demo","country:ABY",123,77,record,bytes,loaded)==-15);
 stamp("demo",200);put("__v64o_demo_i0",0);check("invalid_stamp",Array64_ImportOwned(header,"demo","country:ABY",123,77,record,bytes,loaded)==-13);
 stamp("demo",200);check("valid_owned_import",Array64_ImportOwned(header,"demo","country:ABY",123,77,record,bytes,loaded)==1);check("owned_recover",Array64_Recover(header,"demo",77,loaded,0)==1);test("owned_restored","demo",0,1,1234567890112500LL,2,4,-1);
 check("owned_replay",Array64_ImportOwned(header,"demo","country:ABY",123,77,record,bytes,loaded)==-5);
 check("stale_export_refused",Array64_ExportOwned(s,"country:ABY",123,bad,100000,&bytes)==-16);
 element("demo",0,LLONG_MIN,1);keyput("demo","gen",200000);stamp("demo",300);
 check("same_generation_changed_data_export_refused",Array64_ExportOwned(s,"country:ABY",123,bad,100000,&bytes)==-16);
 for(i=0;i<64;i++){prepare();stamp("demo",200+i);Array64_Capture(header,"demo",2,42,s);check("cycle_export",Array64_ExportOwned(s,"state:335",123,record,100000,&bytes)==1);Array64_SetExisting(header,"demo",0,2,LLONG_MAX,1,5,1);check("cycle_import",Array64_ImportOwned(header,"demo","state:335",123,77,record,bytes,loaded)==1);check("cycle_recover",Array64_Recover(header,"demo",77,loaded,0)==1);}
 reset(16383);make("abcdefghijklmnopqrst",4096);stamp("abcdefghijklmnopqrst",200);Array64_Capture(header,"abcdefghijklmnopqrst",2,42,s);check("large_export",Array64_ExportOwned(s,"character:ABY_Hoshino",123,record,100000,&bytes)==1);Array64_SetExisting(header,"abcdefghijklmnopqrst",0,2,LLONG_MAX,1,5,1);check("large_import",Array64_ImportOwned(header,"abcdefghijklmnopqrst","character:ABY_Hoshino",123,77,record,bytes,loaded)==1);check("large_recover",Array64_Recover(header,"abcdefghijklmnopqrst",77,loaded,0)==1);
 free(s);free(loaded);free(record);free(bad);free(before);printf("checks=%d passed=%d failed=%d\n",checks,checks-failed,failed);return failed?1:0;
}
'''
(out/'fixture.c').write_text(prefix+source+helpers+main,encoding='ascii');vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
(out/'compile.cmd').write_text('@echo off\r\ncall "'+vc+'" >nul\r\ncl /nologo /W4 /TC fixture.c /Fe:fixture.exe >compile.stdout.txt 2>compile.stderr.txt\r\nexit /b %errorlevel%\r\n',encoding='ascii')
p=subprocess.run(['cmd.exe','/c',str(out/'compile.cmd')],cwd=out,capture_output=True)
if p.returncode:print((out/'compile.stdout.txt').read_bytes().decode('mbcs',errors='replace'));raise SystemExit(p.returncode)
p=subprocess.run([str(out/'fixture.exe')],capture_output=True);(out/'stdout.txt').write_bytes(p.stdout);(out/'stderr.txt').write_bytes(p.stderr)
r={'command':sys.argv,'expanded_sha256':hashlib.sha256(source.encode()).hexdigest(),'stdout':p.stdout.decode('ascii'),'stderr':p.stderr.decode('ascii'),'exit':p.returncode,'synthetic_memory_and_write_adapter':True};(out/'result.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r,indent=2));raise SystemExit(p.returncode)
