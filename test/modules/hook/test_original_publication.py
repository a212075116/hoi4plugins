import argparse
import json
import pathlib
import re
import subprocess


parser = argparse.ArgumentParser()
parser.add_argument("source_root", type=pathlib.Path)
parser.add_argument("output", type=pathlib.Path)
args = parser.parse_args()
root, output = args.source_root.resolve(), args.output.resolve()
output.mkdir(parents=True, exist_ok=True)
sdk = root / "src/plugin/SDK_RVA"
variable = (sdk / "variable64/variable64.c").read_text(encoding="utf-8")
language = (sdk / "variable64/variable64_language.inc").read_text(encoding="utf-8")
process = (sdk / "hook/process_block.c").read_text(encoding="utf-8")
def function(text, name):
    match = re.search(r"^(?:static )?[^;\n]+\b" + name + r"\([^;]+?\n\{", text, re.M)
    end, depth = match.end(), 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[match.start():end] + "\n"
prefix = f'#include "{(sdk / "minihook/include/MinHook.h").as_posix()}"\n#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n'
prefix += r'''
static unsigned char* host;static int moduleOn,available,readable,failure,group,foreignRemoved,publishedWrong,callbackFaults,checks,failed,cases;
static void* targets[11];static void** slots[11];static int hook[11];static char trace[4096];static int used;
#define CHECK(x) do{++checks;if(!(x)){++failed;printf("FAIL line=%d\n",__LINE__);}}while(0)
static void event(char c,int i){used+=sprintf_s(trace+used,sizeof(trace)-used,"%c%d;",c,i);}
static int indexof(const void* p){for(int i=0;i<11;++i)if(p==targets[i])return i;return -1;}
static HMODULE MockModuleA(LPCSTR s){(void)s;return moduleOn?(HMODULE)host:NULL;}
static HMODULE MockModuleW(LPCWSTR s){(void)s;return moduleOn?(HMODULE)host:NULL;}
static FARPROC MockProc(HMODULE m,LPCSTR s){(void)m;int i=!strcmp(s,"CreateProcessA")?1:2;return available&(1<<i)?(FARPROC)targets[i]:NULL;}
#define GetModuleHandleA MockModuleA
#define GetModuleHandleW MockModuleW
#define GetProcAddress MockProc
#include "INLINE_SOURCE"
#include "UI_SOURCE"
void Plugin_Log(const char* fmt,...){(void)fmt;}
int NativeMemory_IsReadable(const void* p,size_t n){return p&&n;}
int ConsoleCmd_IsReadable(const void* p,size_t n){int i=indexof(p);CHECK(n==16&&i>=0);return readable&(1<<i);}
static long long __fastcall Original(void* a,void* b){(void)a;(void)b;return 77;}
static long long __fastcall Previous(void* a,void* b){(void)a;(void)b;return 33;}
static int first(void){return group==0?0:group==1?1:group==2?3:group==4?10:4;}
static int targeted(int i){return i==first()||failure>=4&&failure<=6;}
MH_STATUS WINAPI MH_Initialize(void){event('I',0);return failure==7?MH_ERROR_MEMORY_ALLOC:MH_OK;}
const char* WINAPI MH_StatusToString(MH_STATUS s){(void)s;return "mock";}
MH_STATUS WINAPI MH_CreateHook(LPVOID p,LPVOID d,LPVOID* out){int i=indexof(p);event('C',i);CHECK(i>=0&&d);if((failure==1||failure==3||failure==4||failure==6)&&targeted(i))return failure==3||failure==6?MH_ERROR_ALREADY_CREATED:MH_ERROR_MEMORY_ALLOC;hook[i]=1;*out=(void*)Original;return MH_OK;}
MH_STATUS WINAPI MH_EnableHook(LPVOID p){int i=indexof(p);event('E',i);int correct=*slots[i]==(void*)Original;publishedWrong+=!correct;CHECK(correct);
 if(i==0){__try{Hook_UiDateUpdate(NULL,NULL);}__except(EXCEPTION_EXECUTE_HANDLER){++callbackFaults;}}
 if((failure==2||failure==5)&&targeted(i))return MH_ERROR_MEMORY_PROTECT;return MH_OK;
}
MH_STATUS WINAPI MH_RemoveHook(LPVOID p){int i=indexof(p);event('R',i);if(hook[i]==2)++foreignRemoved;hook[i]=0;return MH_OK;}
MH_STATUS WINAPI MH_DisableHook(LPVOID p){(void)p;return MH_OK;}
typedef BOOL (WINAPI *CreateProcessAFn)(LPCSTR,LPSTR,LPSECURITY_ATTRIBUTES,LPSECURITY_ATTRIBUTES,BOOL,DWORD,LPVOID,LPCSTR,LPSTARTUPINFOA,LPPROCESS_INFORMATION);
typedef BOOL (WINAPI *CreateProcessWFn)(LPCWSTR,LPWSTR,LPSECURITY_ATTRIBUTES,LPSECURITY_ATTRIBUTES,BOOL,DWORD,LPVOID,LPCWSTR,LPSTARTUPINFOW,LPPROCESS_INFORMATION);
static CreateProcessAFn g_originalCreateProcessA;static CreateProcessWFn g_originalCreateProcessW;static int g_hookInstalled;
static void Hook_CreateProcessA(void){}static void Hook_CreateProcessW(void){}
typedef long long (__fastcall *Var64GameSetExecFn)(void*,void*);
static Var64GameSetExecFn g_var64OrigGameSetExec,g_var64OrigAddExec,g_var64OrigSubExec,g_var64OrigMulExec,g_var64OrigDivExec,g_var64OrigClampExec,g_var64OrigClearExec;
static int g_var64GameSyntaxHookReady;
typedef void* (__fastcall *Var64VarTextHandlerFn)(void*,const char*,const char*,void*,int);
static Var64VarTextHandlerFn g_var64OrigVarTextHandler;
static void Var64_VarTextBridgeDetour(void){}
static unsigned char* Var64_Image(void){return moduleOn?host:NULL;}
static void Var64_GameSyntaxDetour(void){}static void Var64_AddDetour(void){}static void Var64_SubDetour(void){}static void Var64_MulDetour(void){}static void Var64_DivDetour(void){}static void Var64_ClampDetour(void){}static void Var64_ClearDetour(void){}
'''.replace("INLINE_SOURCE", (sdk / "hook/inline_hook.c").as_posix()).replace("UI_SOURCE", (sdk / "gamedate/gamedate_ui.c").as_posix())
prefix += "\n".join(re.findall(r"^#define RVA_(?:VAR\w*|GAME_SET_EXEC)\s+[^\n]+", variable, re.M)) + "\n"
prefix += function(process, "ApiTarget") + function(process, "ProcBlock_Install")
prefix += function(variable, "Var64_InstallGameSyntaxHook") + function(variable, "Var64_InstallArithmeticHooks")
prefix += re.search(r"^#define RVA_VARTEXT_HANDLER[^\n]+",language,re.M).group(0)+"\n"+function(language,"Var64_InstallLanguageBridge")
main = r'''
int main(void){
 host=(unsigned char*)calloc(1,0x37EC000);if(!host)return 2;
 targets[0]=host+RVA_GD_UI_DATE_UPDATE;targets[1]=host+100;targets[2]=host+200;targets[3]=host+RVA_GAME_SET_EXEC;targets[4]=host+RVA_VAR_ADD_EXEC;targets[5]=host+RVA_VAR_SUB_EXEC;targets[6]=host+RVA_VAR_MUL_EXEC;targets[7]=host+RVA_VAR_DIV_EXEC;targets[8]=host+RVA_VARCLAMP_EXEC;targets[9]=host+RVA_VAR_CLEAR_EXEC;targets[10]=host+RVA_VARTEXT_HANDLER;
 slots[0]=(void**)&g_origUiDate;slots[1]=(void**)&g_originalCreateProcessA;slots[2]=(void**)&g_originalCreateProcessW;slots[3]=(void**)&g_var64OrigGameSetExec;slots[4]=(void**)&g_var64OrigAddExec;slots[5]=(void**)&g_var64OrigSubExec;slots[6]=(void**)&g_var64OrigMulExec;slots[7]=(void**)&g_var64OrigDivExec;slots[8]=(void**)&g_var64OrigClampExec;slots[9]=(void**)&g_var64OrigClearExec;slots[10]=(void**)&g_var64OrigVarTextHandler;
 for(group=0;group<5;++group){int masks=group==0?2:group==1?4:group==2?3:group==4?3:64;
  for(int mask=0;mask<masks;++mask)for(failure=0;failure<8;++failure)for(int seed=0;seed<2;++seed)for(int ready=0;ready<(group==3||group==4?1:2);++ready){
   used=publishedWrong=callbackFaults=foreignRemoved=0;trace[0]=0;g_hookInit=0;memset(hook,0,sizeof(hook));for(int i=0;i<11;++i)*slots[i]=seed?(void*)Previous:NULL;
   g_uiHooked=g_hookInstalled=g_var64GameSyntaxHookReady=ready;g_uiPanel=NULL;moduleOn=group==0?mask!=0:group==2||group==4?mask!=0:1;available=(mask<<1)&6;readable=group==2?(mask==1?1<<3:0):group==4?(mask==1?1<<10:0):mask<<4;
   if(failure==3||failure==6)for(int i=0;i<11;++i)if(targeted(i))hook[i]=2;
   int result=0;if(group==0)result=GameDateUi_Init();else if(group==1)result=ProcBlock_Install();else if(group==2)Var64_InstallGameSyntaxHook();else if(group==3)Var64_InstallArithmeticHooks();else Var64_InstallLanguageBridge();
   CHECK(!foreignRemoved);
   printf("case group=%d mask=%d failure=%d seed=%d ready=%d result=%d flags=%d/%d/%d trace=%s slots=",group,mask,failure,seed,ready,result,g_uiHooked,g_hookInstalled,g_var64GameSyntaxHookReady,trace);
   for(int i=0;i<11;++i)printf("%d,",*slots[i]==NULL?0:*slots[i]==(void*)Previous?1:*slots[i]==(void*)Original?2:3);printf(" publication_wrong=%d callback_faults=%d\n",publishedWrong,callbackFaults);++cases;
  }
 }
 printf("publication_cases=%d checks=%d failed=%d;actual consumers/adaptor,synchronousEnable callback,mocked native,no game\n",cases,checks,failed);free(host);return failed?1:0;
}
'''
(output / "fixture.c").write_text(prefix + main, encoding="ascii")
vc = "C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat"
includes = [sdk / "minihook/include", root / "src/carrier", sdk / "gamedate", sdk / "hook"]
command = 'cmd /d /s /c "' + f'"{vc}" >nul && cl /nologo /W3 /TC /MT ' + " ".join(f'/I"{p}"' for p in includes) + ' fixture.c /Fe:fixture.exe"'
def run(command):
    p = subprocess.run(command, cwd=output, capture_output=True)
    return dict(command=command, cwd=str(output), stdout=p.stdout.decode("utf-8", errors="replace"), stderr=p.stderr.decode("utf-8", errors="replace"), exit=p.returncode)
build = run(command)
result = run([str(output / "fixture.exe")]) if build["exit"] == 0 else build
(output / "result.json").write_text(json.dumps(dict(build=build, result=result, scope="Actual UI/process/scalar installers and adapter;UI callback actual withSEH baseline fault capture,otherdetours controlled;slots checked duringEnable;no real hooks"), indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
raise SystemExit(result["exit"])
