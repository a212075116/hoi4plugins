import hashlib,json,pathlib,subprocess,sys
R=pathlib.Path(__file__).resolve().parents[3];D=R/'test/reports/20261012_variable64_transaction/console_permission';D.mkdir(exist_ok=True)
phase=sys.argv[1];source=pathlib.Path(sys.argv[2]) if len(sys.argv)>2 else R/'src/plugin/SDK_RVA/console/debug_console.c'
text=source.read_text(encoding='utf-8')
implementation=text[text.index('static unsigned char __fastcall ExternalDeveloperPermission'):text.index('static void ReleaseString')] if 'static int DispatchExternal' in text else '''static int DispatchExternal(unsigned char* base,void* manager,CmdResult* result,CmdArgs* args,char* output,size_t size){((long long (__fastcall*)(void*,CmdResult*,CmdArgs*))(base+0x24B4D40))(manager,result,args);return 1;}'''
code=r'''
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include "HEADER"
static int readable=1,network,iron,developer,devCommand,calls,fault;
int ConsoleCmd_IsReadable(const void* p,size_t n){return readable&&p&&n;}
static unsigned char __fastcall Dev(void* p){return !developer;}
static unsigned char __fastcall Net(void* p){return network;}
static unsigned char __fastcall Iron(void* p){return iron;}
static long long __fastcall Native(void* m,CmdResult* out,CmdArgs* args){
 if(fault)RaiseException(0xe0000042,0,0,NULL);
 unsigned char gate=((unsigned char(__fastcall*)(void*))(*(void***)*(void**)((char*)m+80))[2])(*(void**)((char*)m+80));
 out->ok=!(gate&&(network||iron))&&!(gate&&devCommand);if(out->ok)calls++;
 *(unsigned char*)((char*)m+216)=out->ok;*(unsigned char*)((char*)m+217)=out->ok;(*(unsigned*)((char*)m+220))++;
 return (long long)out;
}
IMPLEMENTATION
int main(void){
 int passed=0,total=0,mp,im,dm,cmd,uiValid=1;void* devvt[3]={0,0,Dev};void* netvt[3]={0,0,Net};void* ironvt[3]={0,0,Iron};void** d=devvt;void** n=netvt;void** i=ironvt;
 for(mp=0;mp<2;mp++)for(im=0;im<2;im++)for(dm=0;dm<2;dm++)for(cmd=0;cmd<2;cmd++){
  unsigned char manager[224]={0};CmdResult out={0};CmdArgs args={0};char output[256]={0};int before=calls,accepted,ok;
  network=mp;iron=im;developer=dm;devCommand=cmd;
  *(void**)(manager+80)=&d;*(void**)(manager+144)=&n;*(void**)(manager+208)=&i;
  accepted=DispatchExternal((unsigned char*)((uintptr_t)Native-0x24B4D40),manager,&out,&args,output,sizeof(output));
  ok=mp?(!accepted&&!out.ok&&calls==before):(accepted&&out.ok&&calls==before+1);
  ok=ok&&*(void**)(manager+80)==&d&&*(void**)(manager+144)==&n&&*(void**)(manager+208)==&i;
  ok=ok&&*(unsigned*)(manager+220)==(mp?0:1);total++;passed+=ok;
  uiValid=uiValid&&manager[216]==0&&manager[217]==0;
  printf("%s multiplayer=%d ironman=%d developer=%d developer_command=%d accepted=%d ok=%d calls=%d counter=%u\n",ok?"PASS":"FAIL",mp,im,dm,cmd,accepted,out.ok,calls-before,*(unsigned*)(manager+220));
 }
 UI_PROBE
 EXCEPTION_PROBE
 printf("%d/%d\n",passed,total);return passed==total?0:1;
}
'''.replace('HEADER',(R/'src/plugin/SDK_RVA/console/console_cmd.h').as_posix()).replace('IMPLEMENTATION',implementation).replace('UI_PROBE','if(!uiValid){puts("FAIL ui_state_restore");return 1;}puts("PASS ui_state_restore");' if 'originalUiState' in implementation else '').replace('EXCEPTION_PROBE',r'''{
 unsigned char manager[224]={0};CmdResult out={0};CmdArgs args={0};char output[256]={0};int caught=0;
 network=0;fault=1;*(void**)(manager+80)=&d;*(void**)(manager+144)=&n;*(void**)(manager+208)=&i;
 __try { DispatchExternal((unsigned char*)((uintptr_t)Native-0x24B4D40),manager,&out,&args,output,sizeof(output)); }
 __except(EXCEPTION_EXECUTE_HANDLER){caught=1;}
 if(!caught||*(void**)(manager+80)!=&d){puts("FAIL exception_pointer_restore");return 1;}
 puts("PASS exception_pointer_restore");
}''' if '__finally' in implementation else '')
cpp=D/f'{phase}_permission.c';cpp.write_text(code,encoding='utf-8');exe=D/f'{phase}_permission.exe'
vc='C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat'
cmd=f'"{vc}" >nul && cl /nologo /TC /MT "{cpp}" /Fe:"{exe}" /Fo:"{D/(phase+".obj")}"'
def run(c):
 p=subprocess.run(c,capture_output=True);return dict(command=c,stdout=p.stdout.decode('utf-8',errors='replace'),stderr=p.stderr.decode('utf-8',errors='replace'),exit=p.returncode)
build=run('cmd /d /s /c "'+cmd+'"');result=run([str(exe)]) if not build['exit'] else build
x=dict(phase=phase,source=str(source.resolve()),sha256=hashlib.sha256(source.read_bytes()).hexdigest(),build=build,result=result,scope='Actual DispatchExternal source with controlled native predicate/dispatcher doubles; not real multiplayer/ironman session')
(D/(phase+'.json')).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8');sys.stdout.reconfigure(encoding='utf-8');print(json.dumps(x,ensure_ascii=False,indent=2));sys.exit(result['exit'])
