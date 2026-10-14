import ast,hashlib,json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[3];out=pathlib.Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=True)
def literal(file,name):
    for n in ast.parse(file.read_text(encoding='utf-8')).body:
        if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id==name:return ast.literal_eval(n.value)
    raise ValueError(name)
prefix=literal(ROOT/'test/modules/effect/test_array64_group_native.py','prefix')
helpers=literal(ROOT/'test/modules/effect/test_array64_group_native.py','main').split('int main(void)')[0]+literal(ROOT/'test/modules/effect/test_array64_transaction_native.py','main').split('int main(void)')[0]
folder=(pathlib.Path(sys.argv[2]).resolve() if len(sys.argv)>2 else ROOT)/'src/plugin/SDK_RVA/variable64';source=(folder/'native_array_readonly.c').read_text(encoding='utf-8')
for name,previous in [('array64_group_readonly.c','native_array_readonly.c'),('array64_existing_transaction.c','array64_group_readonly.c'),('array64_recovery.c','array64_existing_transaction.c'),('array64_durable_snapshot.c','array64_recovery.c')]:source=(folder/name).read_text(encoding='utf-8').replace('#include "'+previous+'"',source)
for header in ['array64_wire.h','array64_owner_key.h']:
    directive='#include "'+header+'"'
    if directive in source:source=source.replace(directive,(folder/header).read_text(encoding='utf-8').replace('#pragma once\n',''))
main=r'''
static void rehash(unsigned char* b,unsigned int n){ad_put(b+n-8,ad_hash(b,n-8),8);}
int main(void){Array64Snapshot* s=malloc(sizeof(*s)),*loaded=malloc(sizeof(*s));unsigned char* record=malloc(100000),*bad=malloc(100000),*before=malloc(sizeof(nodes));unsigned int bytes;int i,n,g;long long raw;
 prepare();Array64_Capture(header,"demo",2,42,s);check("export",Array64_ExportBaseline(s,"country:ABY",123,record,100000,&bytes)==1);check("wire_length",bytes==111);check("wire_header",ad_get(record,8)==0x3245534142343641ull&&ad_get(record+8,4)==1&&ad_get(record+12,4)==2);
 check("quarantine",Array64_SetExisting(header,"demo",0,2,LLONG_MAX,1,5,1)==-3);memcpy(before,nodes,sizeof(nodes));calls=0;
 check("wrong_scope",Array64_ImportBaseline(header,"demo","country:ARI",123,77,record,bytes,loaded)==-4);
 check("wrong_lineage",Array64_ImportBaseline(header,"demo","country:ABY",124,77,record,bytes,loaded)==-4);
 check("wrong_name",Array64_ImportBaseline(header,"other","country:ABY",123,77,record,bytes,loaded)==-4);
 memcpy(bad,record,bytes);bad[bytes-1]^=1;check("corrupt",Array64_ImportBaseline(header,"demo","country:ABY",123,77,bad,bytes,loaded)==-3);
 memcpy(bad,record,bytes);ad_put(bad+8,2,4);check("unknown_version",Array64_ImportBaseline(header,"demo","country:ABY",123,77,bad,bytes,loaded)==-2);
 check("truncated",Array64_ImportBaseline(header,"demo","country:ABY",123,77,record,bytes-1,loaded)==-3);
 memcpy(bad,record,bytes);ad_put(bad+16,0xffffffffu,4);check("length_overflow",Array64_ImportBaseline(header,"demo","country:ABY",123,77,bad,bytes,loaded)==-3);
 memcpy(bad,record,bytes);bad[53]=0;rehash(bad,bytes);check("embedded_name_nul",Array64_ImportBaseline(header,"demo","country:ABY",123,77,bad,bytes,loaded)==-3);
 memcpy(bad,record,bytes);ad_put(bad+55+16,500000,8);rehash(bad,bytes);check("invalid_encoding_rehashed",Array64_ImportBaseline(header,"demo","country:ABY",123,77,bad,bytes,loaded)==-3);
 check("all_rejections_no_write",!calls&&!memcmp(before,nodes,sizeof(nodes)));
 check("valid_import",Array64_ImportBaseline(header,"demo","country:ABY",123,77,record,bytes,loaded)==1);check("fresh_owner",loaded->owner==77&&loaded->container==header&&loaded->checksum==ar_hash(loaded));
 check("recovery",Array64_Recover(header,"demo",77,loaded,0)==1);test("restored","demo",0,1,1234567890112500LL,2,4,-1);
 check("record_replay_even",Array64_ImportBaseline(header,"demo","country:ABY",123,99,record,bytes,loaded)==-5);
 Array64_Capture(header,"demo",4,42,s);Array64_SetExisting(header,"demo",0,4,LLONG_MAX,1,5,1);check("old_record_reject_new_odd",Array64_ImportBaseline(header,"demo","country:ABY",123,77,record,bytes,loaded)==-5);
 check("scope_canonical",ad_scope("state:335")&&ad_scope("character:ABY_Hoshino")&&ad_scope("global")&&!ad_scope("state:0335")&&!ad_scope("country:aby")&&!ad_scope("global.")&&!ad_scope("state:2147483648"));
 prepare();Array64_Capture(header,"demo",2,42,s);unsigned int sentinel=999;memset(bad,0x55,100000);check("capacity_no_write",Array64_ExportBaseline(s,"country:ABY",123,bad,1,&sentinel)==-2&&sentinel==999&&bad[0]==0x55);
 for(i=0;i<64;i++){prepare();long long want=i%2?LLONG_MIN:LLONG_MAX;element("demo",0,want,1);check("cycle_capture",Array64_Capture(header,"demo",2,42,s)==1);check("cycle_export",Array64_ExportBaseline(s,"state:335",123,record,100000,&bytes)==1);check("cycle_isolate",Array64_SetExisting(header,"demo",0,2,-1,1,5,1)==-3);check("cycle_import",Array64_ImportBaseline(header,"demo","state:335",123,77,record,bytes,loaded)==1);check("cycle_recovery",Array64_Recover(header,"demo",77,loaded,0)==1);check("cycle_read",Array64Group_Read(header,"demo",0,4,&raw,&n,&g)==1&&raw==want);}
 reset(16383);make("abcdefghijklmnopqrst",4096);check("large_capture",Array64_Capture(header,"abcdefghijklmnopqrst",2,42,s)==1);check("large_export",Array64_ExportBaseline(s,"character:ABY_Hoshino",123,record,100000,&bytes)==1);check("large_isolate",Array64_SetExisting(header,"abcdefghijklmnopqrst",0,2,LLONG_MAX,1,5,1)==-3);check("large_import",Array64_ImportBaseline(header,"abcdefghijklmnopqrst","character:ABY_Hoshino",123,77,record,bytes,loaded)==1);check("large_recovery",Array64_Recover(header,"abcdefghijklmnopqrst",77,loaded,0)==1);
 free(s);free(loaded);free(record);free(bad);free(before);printf("checks=%d passed=%d failed=%d\n",checks,checks-failed,failed);return failed?1:0;
}
'''
(out/'fixture.c').write_text(prefix+source+helpers+main,encoding='ascii');vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
(out/'compile.cmd').write_text('@echo off\r\ncall "'+vc+'" >nul\r\ncl /nologo /W4 /TC fixture.c /Fe:fixture.exe >compile.stdout.txt 2>compile.stderr.txt\r\nexit /b %errorlevel%\r\n',encoding='ascii')
p=subprocess.run(['cmd.exe','/c',str(out/'compile.cmd')],cwd=out,capture_output=True)
if p.returncode:print((out/'compile.stdout.txt').read_bytes().decode('mbcs',errors='replace'));raise SystemExit(p.returncode)
p=subprocess.run([str(out/'fixture.exe')],capture_output=True);(out/'stdout.txt').write_bytes(p.stdout);(out/'stderr.txt').write_bytes(p.stderr)
r={'command':sys.argv,'expanded_sha256':hashlib.sha256(source.encode()).hexdigest(),'stdout':p.stdout.decode('ascii'),'stderr':p.stderr.decode('ascii'),'exit':p.returncode,'synthetic_memory_and_write_adapter':True}
(out/'result.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r,indent=2));raise SystemExit(p.returncode)
