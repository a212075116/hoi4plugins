import json
import pathlib
import re
import subprocess
import sys

root=pathlib.Path(sys.argv[1]).resolve();out=pathlib.Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
text=(root/'src/plugin/plugin_main.c').read_text(encoding='utf-8-sig')
start=text.index('static DWORD WINAPI PluginThread(');opening=text.index('{',start);end=opening+1;depth=1
while depth:
    depth+=(text[end]=='{')-(text[end]=='}');end+=1
body=text[start:end]
prefix=r'''
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
static int legacy,known,initialized,viewer,monitor,noCamera,cameraCalls,partialProcess,processDisabled;
typedef struct {const char* name;int(*run)(void);int expected;int(*ready)(void);int complete;int last;} PluginRegistrationStep;
static PluginRegistrationStep g_effectSteps[6]={{"camera",NULL,4,NULL,0,0}},g_triggerSteps[2];
#define RVA_GS_GLOBAL 0
static HMODULE FakeBase(void* p){return NULL;}
static void FakeSleep(DWORD n){}
#define GetModuleHandleA FakeBase
#define Sleep FakeSleep
static void Plugin_Log(const char* fmt,...){}
static int NativeAdapter_Initialize(void){++initialized;return known;}
static int NativeAdapter_LegacyAllowed(void){return known;}
static int NativeAdapter_CameraWriteAllowed(void){return known&&!noCamera;}
static const char* NativeAdapter_Diagnostic(void){return "fixture";}
static void NativeAdapter_Report(const char* n,int ok,const char* r){}
static void NativeAdapter_StartMonitor(void){++monitor;}
static void NativeAdapter_OpenLogConsole(void){++viewer;}
static void NativeAdapter_CameraRegistered(int a,int b){}
static int Camera_RegisterReadCommand(void){return 1;}
static const char* FileRedirect_GameRoot(void){return "fixture";}
static int ProcBlock_Complete(void){return !partialProcess;}
static void ProcBlock_SetEnabled(int enabled){processDisabled=!enabled;}
static void DebugConsole_Start(void){++legacy;}
static void DebugConsole_RegisterCommands(void){++legacy;}
static int Effect_RegistryReady(void){return 1;}
static int Trigger_RegistryReady(void){return 1;}
static void RegisterPluginGroups(const char* name,int(*ready)(void),PluginRegistrationStep* s,int n){++legacy;for(int i=0;i<n;++i){s[i].complete=1;s[i].last=s[i].expected;}}
static void VerifyClassStructure(void){++legacy;}
'''
for name in ['AchievementSource_Install','AchievementCompat_Install','AchievementUi_Install','FileRedirect_Install','ProcBlock_Install','Camera_CaptureTrueUpperLimit','GameDate_RegisterCommands','GameDateUi_Init','CrashTest_RegisterCommands','AchievementProbe_RegisterCommands','AchievementCompat_RegisterCommands','AchievementUi_RegisterCommands','ScanKnownArrays']:
    prefix+='static int '+name+'(void){++legacy;return '+('3' if name=='Camera_RegisterCommands' else '1')+';}\n'
prefix+='static int Camera_RegisterCommands(void){++legacy;++cameraCalls;return 3;}\n'
main=r'''
int main(int argc,char** argv){known=argc>1;noCamera=known&&!strcmp(argv[1],"known-no-camera");partialProcess=known&&!strcmp(argv[1],"known-partial-process");PluginThread(NULL);printf("known=%d legacy_calls=%d initialized=%d viewer=%d monitor=%d camera_commands=%d camera_expected=%d process_disabled=%d\n",known,legacy,initialized,viewer,monitor,cameraCalls,g_effectSteps[0].expected,processDisabled);return !known&&legacy?1:0;}
'''
(out/'gate.c').write_text(prefix+body+main,encoding='ascii')
vc='C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat'
compile=f'"{vc}" >nul && cl /nologo /W3 /TC /O2 gate.c /Fe:gate.exe'
records=[]
for command,shell in [(compile,True),([str(out/'gate.exe')],False),([str(out/'gate.exe'),'known'],False),([str(out/'gate.exe'),'known-no-camera'],False),([str(out/'gate.exe'),'known-partial-process'],False)]:
    p=subprocess.run(command,shell=shell,cwd=out,capture_output=True)
    records.append(dict(command=command,stdout=p.stdout.decode('utf-8',errors='replace'),stderr=p.stderr.decode('utf-8',errors='replace'),exit=p.returncode))
    if command==compile and p.returncode:break
result=dict(source=str(root/'src/plugin/plugin_main.c'),commands=records,scope='Actual PluginThread body; all business callees controlled. Unknown gate must precede every old business entry; real mapped-image identity separately tested.')
(out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
raise SystemExit(records[0]['exit'])
