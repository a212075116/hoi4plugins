import ast,hashlib,json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[3];out=pathlib.Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=True)
def literal(path,name):
    tree=ast.parse(path.read_text(encoding='utf-8'))
    for n in tree.body:
        if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id==name:return ast.literal_eval(n.value)
    raise ValueError(name)
group_test=ROOT/'test/modules/effect/test_array64_group_native.py';tx_test=ROOT/'test/modules/effect/test_array64_transaction_native.py'
prefix=literal(group_test,'prefix');helpers=literal(group_test,'main').split('int main(void)')[0]+literal(tx_test,'main').split('int main(void)')[0]
base=(ROOT/'src/plugin/SDK_RVA/variable64/native_array_readonly.c').read_text(encoding='utf-8')
group=(ROOT/'src/plugin/SDK_RVA/variable64/array64_group_readonly.c').read_text(encoding='utf-8').replace('#include "native_array_readonly.c"',base)
tx=(ROOT/'src/plugin/SDK_RVA/variable64/array64_existing_transaction.c').read_text(encoding='utf-8').replace('#include "array64_group_readonly.c"',group)
source=(ROOT/'src/plugin/SDK_RVA/variable64/array64_recovery.c').read_text(encoding='utf-8').replace('#include "array64_existing_transaction.c"',tx)
main=r'''
int main(void){Array64Snapshot* saved=malloc(sizeof(Array64Snapshot)),*bad=malloc(sizeof(Array64Snapshot));unsigned char* before=malloc(sizeof(nodes));int s,n,g,i,j;long long raw;
 prepare();check("capture",Array64_Capture(header,"demo",2,42,saved)==1);check("snapshot_size",Array64_SnapshotBytes()==sizeof(*saved));
 s=Array64_SetExisting(header,"demo",0,2,LLONG_MAX,1,5,1);check("quarantine",s==-3);check("inspect",Array64_InspectQuarantine(header,"demo",&n,&g)==1&&n==2&&g==3);
 memcpy(before,nodes,sizeof(nodes));memcpy(bad,saved,sizeof(*saved));bad->checksum^=1;calls=0;s=Array64_Recover(header,"demo",42,bad,0);check("checksum_no_write",s==-1&&!calls&&!memcmp(before,nodes,sizeof(nodes)));
 s=Array64_Recover(header,"demo",43,saved,0);check("owner_no_write",s==-1&&!calls&&!memcmp(before,nodes,sizeof(nodes)));
 s=Array64_Recover(header+8,"demo",42,saved,0);check("container_no_write",s==-1&&!calls&&!memcmp(before,nodes,sizeof(nodes)));
 s=Array64_Recover(header,"other",42,saved,0);check("name_no_write",s==-1&&!calls&&!memcmp(before,nodes,sizeof(nodes)));
 memcpy(bad,saved,sizeof(*saved));bad->parts[1][2]=500000;bad->checksum=ar_hash(bad);s=Array64_Recover(header,"demo",42,bad,0);check("invalid_encoding_even_if_rehashed",s==-1&&!calls&&!memcmp(before,nodes,sizeof(nodes)));
 s=Array64_Recover(header,"demo",42,saved,0);check("recovery",s==1);test("recovered_value","demo",0,1,1234567890112500LL,2,4,-1);test("neighbor","demo",1,1,-1,2,4,-1);
 memcpy(before,nodes,sizeof(nodes));calls=0;s=Array64_Recover(header,"demo",42,saved,0);check("consumed_no_write",s==-1&&!calls&&!memcmp(before,nodes,sizeof(nodes)));
 for(i=1;i<=7;i++){prepare();Array64_Capture(header,"demo",2,42,saved);Array64_SetExisting(header,"demo",0,2,LLONG_MAX,1,5,1);s=Array64_Recover(header,"demo",42,saved,i);check("recovery_boundary_failure",s==-3&&!saved->consumed);test("remains_odd","demo",0,-5,123,-99,-99,-1);s=Array64_Recover(header,"demo",42,saved,0);check("retry",s==1);test("retry_value","demo",0,1,1234567890112500LL,2,4,-1);}
 prepare();Array64_Capture(header,"demo",2,42,bad);Array64_SetExisting(header,"demo",0,2,LLONG_MIN,1,0,0);Array64_Capture(header,"demo",4,42,saved);Array64_SetExisting(header,"demo",0,4,LLONG_MAX,1,5,1);calls=0;memcpy(before,nodes,sizeof(nodes));s=Array64_Recover(header,"demo",42,bad,0);check("stale_no_write",s==-2&&!calls&&!memcmp(before,nodes,sizeof(nodes)));check("current_snapshot",Array64_Recover(header,"demo",42,saved,0)==1);test("new_even_generation","demo",0,1,LLONG_MIN,2,6,-1);
 prepare();Array64_Capture(header,"demo",2,42,saved);check("failed_capture_invalidates",Array64_Capture(header,"demo",2,0,saved)==-1&&saved->magic==0);
 prepare();Array64_Capture(header,"demo",2,42,saved);Array64_SetExisting(header,"demo",0,2,LLONG_MAX,1,5,1);keyput("demo","hi^num",100000);calls=0;memcpy(before,nodes,sizeof(nodes));check("changed_shape_no_write",Array64_Recover(header,"demo",42,saved,0)==-2&&!calls&&!memcmp(before,nodes,sizeof(nodes)));
 prepare();Array64_Capture(header,"demo",2,42,saved);Array64_SetExisting(header,"demo",0,2,LLONG_MAX,1,5,1);keyput("demo","kind^0",500000);check("partial_encoding_can_recover",Array64_Recover(header,"demo",42,saved,0)==1);test("partial_encoding_restored","demo",0,1,1234567890112500LL,2,4,-1);
 for(i=1;i<=7;i++)for(j=0;j<=1;j++){prepare();Array64_Capture(header,"demo",2,42,saved);Array64_SetExisting(header,"demo",0,2,LLONG_MAX,1,5,1);calls=0;reject_call=i;after_write=j;s=Array64_Recover(header,"demo",42,saved,0);check("adapter_failures_not_consumed",s==-3&&!saved->consumed);test("adapter_failure_odd","demo",0,-5,123,-99,-99,-1);reject_call=0;check("adapter_failure_retry",Array64_Recover(header,"demo",42,saved,0)==1);}
 prepare();int gen=2;for(i=0;i<256;i++){long long want=i%2?250000:LLONG_MIN;check("pressure_commit",Array64_SetExisting(header,"demo",0,gen,want,i%2?0:1,0,0)==1);gen+=2;check("pressure_capture",Array64_Capture(header,"demo",gen,42,saved)==1);check("pressure_quarantine",Array64_SetExisting(header,"demo",0,gen,LLONG_MAX,1,5,1)==-3);check("pressure_recover",Array64_Recover(header,"demo",42,saved,0)==1);gen+=2;check("pressure_read",Array64Group_Read(header,"demo",0,gen,&raw,&n,&g)==1&&raw==want&&n==2&&g==gen);}
 check("scalar_untouched",na_lookup(header,"demo",&raw)==1&&raw==100000);check("native_array_untouched",na_lookup(header,"demo^0",&raw)==1&&raw==250000);
 reset(16383);make("demo",4096);check("large_capture",Array64_Capture(header,"demo",2,42,saved)==1);check("large_quarantine",Array64_SetExisting(header,"demo",0,2,LLONG_MAX,1,5,1)==-3);check("large_recovery",Array64_Recover(header,"demo",42,saved,0)==1);test("large_neighbor","demo",4095,1,409487500,4096,4,-1);
 free(before);free(saved);free(bad);printf("checks=%d passed=%d failed=%d\n",checks,checks-failed,failed);return failed?1:0;
}
'''
(out/'fixture.c').write_text(prefix+source+helpers+main,encoding='ascii');vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
(out/'compile.cmd').write_text('@echo off\r\ncall "'+vc+'" >nul\r\ncl /nologo /W4 /TC fixture.c /Fe:fixture.exe >compile.stdout.txt 2>compile.stderr.txt\r\nexit /b %errorlevel%\r\n',encoding='ascii')
p=subprocess.run(['cmd.exe','/c',str(out/'compile.cmd')],cwd=out,capture_output=True)
if p.returncode:print((out/'compile.stdout.txt').read_bytes().decode('mbcs',errors='replace'));raise SystemExit(p.returncode)
p=subprocess.run([str(out/'fixture.exe')],capture_output=True);(out/'stdout.txt').write_bytes(p.stdout);(out/'stderr.txt').write_bytes(p.stderr)
r={'command':sys.argv,'expanded_sha256':hashlib.sha256(source.encode()).hexdigest(),'stdout':p.stdout.decode('ascii'),'stderr':p.stderr.decode('ascii'),'exit':p.returncode,'synthetic_memory_and_write_adapter':True}
(out/'result.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r,indent=2));raise SystemExit(p.returncode)
