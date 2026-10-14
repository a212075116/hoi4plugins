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
def function(text, name):
    match = re.search(r"^int " + name + r"\(void\)\s*\{", text, re.M)
    end, depth = match.end(), 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[match.start():end] + "\n"
prefix = f'#include "{(sdk / "minihook/include/MinHook.h").as_posix()}"\n'
prefix += r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned char* host;
static void* targets[5];static int count,createFail,queueFail,applyFail,foreign,cleanupMask,initStatus;
static int hook[5],queued[5],enabled[5],creates,applies,foreignRemoved,checks,failed,cases;
static char trace[2048];static int length;
static void event(char op,int index){length+=sprintf_s(trace+length,sizeof(trace)-length,"%c%d;",op,index);}
static int indexof(void* p){for(int i=0;i<count;++i)if(targets[i]==p)return i;return -1;}
static HMODULE MockModule(LPCWSTR p){(void)p;return (HMODULE)host;}
static FARPROC MockProc(HMODULE p,LPCSTR n){(void)p;(void)n;return (FARPROC)1;}
#define GetModuleHandleW MockModule
#define GetProcAddress MockProc
#include "INLINE_SOURCE"
void Plugin_Log(const char* fmt,...){(void)fmt;}
MH_STATUS WINAPI MH_Initialize(void){event('I',0);return (MH_STATUS)initStatus;}
const char* WINAPI MH_StatusToString(MH_STATUS s){(void)s;return "mock";}
MH_STATUS WINAPI MH_CreateHook(LPVOID p,LPVOID d,LPVOID* out){int i=indexof(p);event('C',i);++creates;if(!d||i<0)return MH_ERROR_NOT_EXECUTABLE;if(i==createFail)return foreign?MH_ERROR_ALREADY_CREATED:MH_ERROR_MEMORY_ALLOC;hook[i]=1;*out=(void*)(size_t)(0x100+i);return MH_OK;}
MH_STATUS WINAPI MH_QueueEnableHook(LPVOID p){int i=indexof(p);event('Q',i);if(i==queueFail)return MH_ERROR_MEMORY_PROTECT;queued[i]=1;return MH_OK;}
MH_STATUS WINAPI MH_QueueDisableHook(LPVOID p){int i=indexof(p);event('q',i);if(cleanupMask&1)return MH_ERROR_MEMORY_PROTECT;queued[i]=0;return MH_OK;}
MH_STATUS WINAPI MH_EnableHook(LPVOID p){int i=indexof(p);event('E',i);if(queueFail==i)return MH_ERROR_MEMORY_PROTECT;enabled[i]=1;return MH_OK;}
MH_STATUS WINAPI MH_DisableHook(LPVOID p){int i=indexof(p);event('D',i);if(cleanupMask&2)return MH_ERROR_MEMORY_PROTECT;enabled[i]=0;return MH_OK;}
MH_STATUS WINAPI MH_ApplyQueued(void){event('A',0);++applies;if((applies==1&&applyFail)||(applies>1&&(cleanupMask&4)))return MH_ERROR_MEMORY_PROTECT;for(int i=0;i<count;++i)enabled[i]=queued[i];return MH_OK;}
MH_STATUS WINAPI MH_RemoveHook(LPVOID p){int i=indexof(p);event('R',i);if(hook[i]==2)++foreignRemoved;if(cleanupMask&8)return MH_ERROR_MEMORY_PROTECT;hook[i]=enabled[i]=queued[i]=0;return MH_OK;}
static volatile LONG g_installed,g_sourceInstalled,g_uiInstalled;
static unsigned char* g_base;static unsigned char* g_uiBase;
static void* g_eligible,*g_iron,*g_rebuild,*g_restore,*g_update,*g_exists,*g_lexer,*g_loadDefinitions,*g_mountMemory,*g_realDir,*g_frontUpdate,*g_frontTooltip;
static void Eligible(void){}static void Iron(void){}static void Rebuild(void){}static void Restore(void){}static void Update(void){}
static void SourceExists(void){}static void SourceLexer(void){}static void SourceLoad(void){}static void FrontUpdate(void){}static void FrontTooltip(void){}
int AchievementCompat_Installed(void){return 1;}
static int SourceHostSupported(unsigned char* p){return p!=NULL;}
'''.replace("INLINE_SOURCE", (sdk / "hook/inline_hook.c").as_posix())
header = sdk / "hook/inline_hook_batch.h"
if header.exists():
    prefix += f'#include "{header.as_posix()}"\n'
for file, name in [("achievement_compat.c", "AchievementCompat_Install"), ("achievement_probe.c", "AchievementSource_Install"), ("achievement_ui.c", "AchievementUi_Install")]:
    prefix += function((sdk / "achievement" / file).read_text(encoding="utf-8"), name)
main = r'''
#define CHECK(x) do{++checks;if(!(x)){++failed;printf("FAIL line=%d\n",__LINE__);}}while(0)
static void reset(int n){count=n;memset(hook,0,sizeof(hook));memset(queued,0,sizeof(queued));memset(enabled,0,sizeof(enabled));creates=applies=foreignRemoved=length=0;trace[0]=0;g_installed=g_sourceInstalled=g_uiInstalled=0;g_hookInit=0;initStatus=0;}
int main(void){
 host=(unsigned char*)calloc(1,0x37EC000);if(!host)return 2;
 IMAGE_DOS_HEADER* dos=(IMAGE_DOS_HEADER*)host;dos->e_magic=IMAGE_DOS_SIGNATURE;dos->e_lfanew=256;IMAGE_NT_HEADERS64* nt=(IMAGE_NT_HEADERS64*)(host+256);nt->Signature=IMAGE_NT_SIGNATURE;nt->FileHeader.TimeDateStamp=0x6AA123BB;nt->OptionalHeader.SizeOfImage=0x37EC000;
 for(int module=0;module<3;++module){
  int n=module==0?5:module==1?3:2;
  for(int cf=-1;cf<n;++cf)for(int qf=-1;qf<n;++qf)for(int af=0;af<2;++af)for(int fr=0;fr<2;++fr)for(int mask=0;mask<16;mask+=5){
   reset(n);createFail=cf;queueFail=qf;applyFail=af;foreign=fr;cleanupMask=mask;
   size_t offsets[5]={0x6201F0,0x3DB5C0,0x6202C0,0x620570,0x621040};if(module==1){offsets[0]=0x24DC920;offsets[1]=0x24BB300;offsets[2]=0x6207E0;}if(module==2){offsets[0]=0x1CDA120;offsets[1]=0x1CD4570;}
   for(int i=0;i<n;++i)targets[i]=host+offsets[i];if(fr&&cf>=0)hook[cf]=2;
   int result=module==0?AchievementCompat_Install():module==1?AchievementSource_Install():AchievementUi_Install();int expected=cf<0&&qf<0&&!af;
   CHECK(result==expected);CHECK((module==0?g_installed:module==1?g_sourceInstalled:g_uiInstalled)==expected);CHECK(!foreignRemoved);if(fr&&cf>=0)CHECK(hook[cf]==2);
   printf("group=%d cf=%d qf=%d af=%d foreign=%d mask=%d result=%d trace=%s state=",module,cf,qf,af,fr,mask,result,trace);for(int i=0;i<n;++i)printf("%d,%d,%d;",hook[i],queued[i],enabled[i]);printf("\n");++cases;
  }
  reset(n);createFail=queueFail=-1;applyFail=foreign=cleanupMask=0;initStatus=MH_ERROR_MEMORY_ALLOC;CHECK(!(module==0?AchievementCompat_Install():module==1?AchievementSource_Install():AchievementUi_Install())&&creates==0);++cases;
 }
 for(int status=0;status<=MH_ERROR_FUNCTION_NOT_FOUND;++status){
  reset(1);targets[0]=host+512;createFail=0;queueFail=-1;applyFail=0;foreign=status==MH_ERROR_ALREADY_CREATED;cleanupMask=0;initStatus=status;
  void* result=InlineHook_Install(targets[0],(void*)1);CHECK(result==NULL);CHECK(creates==(status==MH_OK));++cases;
  reset(1);targets[0]=host+512;createFail=-1;queueFail=0;applyFail=foreign=0;cleanupMask=0;result=InlineHook_Install(targets[0],(void*)1);CHECK(result==NULL&&hook[0]==0);++cases;
  reset(1);targets[0]=host+512;hook[0]=1;cleanupMask=status?2:0;CHECK(InlineHook_Remove(targets[0])==(status==0));CHECK(status==0?hook[0]==0:hook[0]==1);++cases;
 }
 reset(1);createFail=queueFail=-1;applyFail=foreign=cleanupMask=0;CHECK(!InlineHook_Install(NULL,(void*)1)&&!InlineHook_Install((void*)1,NULL)&&!InlineHook_Remove(NULL)&&creates==0);++cases;
 printf("hook_cases=%d checks=%d failed=%d;actual adapters and installers,mocked MinHook,no game hooks\n",cases,checks,failed);free(host);return failed?1:0;
}
'''
(output / "fixture.c").write_text(prefix + main, encoding="ascii")
vc = "C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat"
command = 'cmd /d /s /c "' + f'"{vc}" >nul && cl /nologo /W3 /TC /MT /I"{sdk / "minihook/include"}" /I"{root / "src/carrier"}" fixture.c /Fe:fixture.exe' + '"'
def run(command):
    p = subprocess.run(command, cwd=output, capture_output=True)
    return dict(command=command, cwd=str(output), stdout=p.stdout.decode("utf-8", errors="replace"), stderr=p.stderr.decode("utf-8", errors="replace"), exit=p.returncode)
build = run(command)
result = run([str(output / "fixture.exe")]) if build["exit"] == 0 else build
(output / "result.json").write_text(json.dumps(dict(build=build, result=result, scope="Actual InlineHook adapter and three production installer definitions; MinHook states/calls controlled; cleanup errors retained; no hooks installed"), indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
raise SystemExit(result["exit"])
