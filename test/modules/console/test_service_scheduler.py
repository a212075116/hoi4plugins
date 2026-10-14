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
text = (sdk / "console/debug_console.c").read_text(encoding="utf-8")
match = re.search(r"^static DWORD WINAPI StartDebugService\([^;]+?\{", text, re.M)
end, depth = match.end(), 1
while depth:
    depth += (text[end] == "{") - (text[end] == "}")
    end += 1
pending = text[text.index("typedef struct {"):text.index("static SRWLOCK g_lock")]
prefix = f'#include "{(root / "src/debug_console/protocol.h").as_posix()}"\n#include <sddl.h>\n#include <shellapi.h>\n#include "{(sdk / "minihook/include/MinHook.h").as_posix()}"\n'
prefix += r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static int mode,pipeCalls,eventCalls,threadCalls,openHelper,localLive,tokenLive,hook,enabled,removeCalls,checks,failed;
static int pipes[5],events[32],foreignRemoved;static unsigned char* host;static char trace[4096];static int used;
static DWORD g_thread;static volatile LONG g_started;static long long (__fastcall *g_frame)(long long,char);
#define CHECK(x) do{++checks;if(!(x)){++failed;printf("FAIL mode=%d line=%d\n",mode,__LINE__);}}while(0)
static void event(char code,int n){used+=sprintf_s(trace+used,sizeof(trace)-used,"%c%d;",code,n);}
static long long __fastcall Original(long long p,char c){(void)p;(void)c;return 0;}
static long long __fastcall Frame(long long p,char c){(void)p;(void)c;return 0;}
static DWORD WINAPI Peer(LPVOID p){(void)p;return 0;}
static BOOL CALLBACK FindWindowThread(HWND h,LPARAM p){(void)h;(void)p;return TRUE;}
static void OpenHelper(void){++openHelper;event('H',0);}
static HMODULE MockModule(LPCWSTR p){(void)p;return (HMODULE)host;}
static HANDLE WINAPI MockCurrent(void){return (HANDLE)1;}
static DWORD WINAPI MockPid(void){return 1234;}
static BOOL WINAPI MockToken(HANDLE p,DWORD rights,PHANDLE out){event('T',0);CHECK(p==(HANDLE)1&&rights==TOKEN_QUERY);if(mode==2)return FALSE;tokenLive=1;*out=(HANDLE)0x11;return TRUE;}
static BOOL WINAPI MockTokenInfo(HANDLE p,TOKEN_INFORMATION_CLASS c,LPVOID out,DWORD size,PDWORD needed){event('t',out?1:0);CHECK(p==(HANDLE)0x11&&c==TokenUser);*needed=sizeof(TOKEN_USER);if(!out)return FALSE;if(mode==4)return FALSE;CHECK(size==sizeof(TOKEN_USER));((TOKEN_USER*)out)->User.Sid=(void*)1;return TRUE;}
static HLOCAL WINAPI MockAlloc(UINT flags,SIZE_T size){event('L',(int)size);CHECK(flags==LPTR);if(mode==3)return NULL;++localLive;return calloc(1,size);}
static HLOCAL WINAPI MockFree(HLOCAL p){event('F',0);CHECK(p&&localLive>0);--localLive;free(p);return NULL;}
static BOOL WINAPI MockSid(PSID p,LPWSTR* out){event('S',0);CHECK(p==(void*)1);if(mode==5)return FALSE;*out=(LPWSTR)calloc(32,sizeof(wchar_t));++localLive;wcscpy_s(*out,32,L"S-1-5-21");return TRUE;}
static BOOL WINAPI MockSd(LPCWSTR s,DWORD revision,PSECURITY_DESCRIPTOR* out,PULONG size){event('s',0);CHECK(revision==SDDL_REVISION_1&&wcsstr(s,L"S-1-5-21")&&!size);if(mode==6)return FALSE;*out=calloc(1,16);++localLive;return TRUE;}
static HANDLE WINAPI MockPipe(LPCWSTR name,DWORD flags,DWORD modes,DWORD instances,DWORD out,DWORD in,DWORD timeout,LPSECURITY_ATTRIBUTES sa){int i=pipeCalls++;event('P',i);CHECK(name&&flags==(PIPE_ACCESS_DUPLEX|FILE_FLAG_OVERLAPPED|((i&&i!=DC_PEERS)?0:FILE_FLAG_FIRST_PIPE_INSTANCE))&&modes==(PIPE_TYPE_BYTE|PIPE_READMODE_BYTE|PIPE_WAIT|PIPE_REJECT_REMOTE_CLIENTS)&&instances==(i==DC_PEERS?1:DC_PEERS)&&out==DC_OUTPUT_MAX+32&&in==DC_INPUT_MAX+32&&timeout==5000&&sa&&sa->lpSecurityDescriptor&&!sa->bInheritHandle);if((mode==7&&i==0)||(mode==8&&i==2)||(mode==9&&i==4))return INVALID_HANDLE_VALUE;pipes[i]=1;return (HANDLE)(size_t)(0x100+i);}
static HANDLE WINAPI MockEvent(LPSECURITY_ATTRIBUTES sa,BOOL manual,BOOL initial,LPCWSTR name){int i=eventCalls++;event('V',i);CHECK(!sa&&manual&&!initial&&!name);if((mode==10&&i==0)||(mode==11&&i==7)||(mode==12&&i==31))return NULL;events[i]=1;return (HANDLE)(size_t)(0x200+i);}
static BOOL WINAPI MockClose(HANDLE h){size_t n=(size_t)h;if(n==0x11){event('c',0);CHECK(tokenLive);tokenLive=0;}else if(n>=0x100&&n<0x105){event('p',(int)n-0x100);CHECK(pipes[n-0x100]);pipes[n-0x100]=0;}else if(n>=0x200&&n<0x220){event('v',(int)n-0x200);CHECK(events[n-0x200]);events[n-0x200]=0;}else{event('r',(int)n-0x400);CHECK(n>=0x400&&n<0x405);}return TRUE;}
static BOOL WINAPI MockEnum(WNDENUMPROC p,LPARAM value){CHECK(p==FindWindowThread&&!value);if(mode!=13){g_thread=77;event('W',0);}return TRUE;}
static void WINAPI MockSleep(DWORD n){CHECK(n==100);}
static HANDLE WINAPI MockThread(LPSECURITY_ATTRIBUTES sa,SIZE_T stack,LPTHREAD_START_ROUTINE p,LPVOID arg,DWORD flags,LPDWORD id){int i=threadCalls++;event('R',i);CHECK(!sa&&!stack&&p==Peer&&arg==(HANDLE)(size_t)(0x100+i)&&!flags&&!id&&g_started==1);return mode==21?NULL:(HANDLE)(size_t)(0x400+i);}
static LPWSTR WINAPI MockCommand(void){return (LPWSTR)L"fixture";}
static LPWSTR* WINAPI MockArgv(LPCWSTR p,int* argc){(void)p;event('A',0);*argc=mode==20?3:mode==19?2:1;LPWSTR* argv=(LPWSTR*)calloc(3,sizeof(LPWSTR));++localLive;argv[0]=(LPWSTR)L"fixture";argv[1]=(LPWSTR)L"-debug";argv[2]=(LPWSTR)L"-no-plugin-console";return argv;}
#define GetModuleHandleW MockModule
#define GetCurrentProcess MockCurrent
#define GetCurrentProcessId MockPid
#define OpenProcessToken MockToken
#define GetTokenInformation MockTokenInfo
#define LocalAlloc MockAlloc
#define LocalFree MockFree
#define ConvertSidToStringSidW MockSid
#define ConvertStringSecurityDescriptorToSecurityDescriptorW MockSd
#define CreateNamedPipeW MockPipe
#define CreateEventW MockEvent
#define CloseHandle MockClose
#define EnumWindows MockEnum
#define Sleep MockSleep
#define CreateThread MockThread
#define GetCommandLineW MockCommand
#define CommandLineToArgvW MockArgv
'''
prefix += f'#include "{(sdk / "hook/inline_hook.c").as_posix()}"\n'
prefix += r'''
void Plugin_Log(const char* fmt,...){(void)fmt;}
MH_STATUS WINAPI MH_Initialize(void){event('I',0);return mode==14?MH_ERROR_MEMORY_ALLOC:mode==23?MH_ERROR_ALREADY_INITIALIZED:MH_OK;}
const char* WINAPI MH_StatusToString(MH_STATUS s){(void)s;return "mock";}
MH_STATUS WINAPI MH_CreateHook(LPVOID p,LPVOID d,LPVOID* out){event('C',0);CHECK(p==host+0xDD3A50&&d==(void*)Frame);if(mode==15)return MH_ERROR_MEMORY_ALLOC;if(mode==16)return MH_ERROR_ALREADY_CREATED;hook=1;*out=(void*)Original;return MH_OK;}
MH_STATUS WINAPI MH_EnableHook(LPVOID p){event('E',0);CHECK(p==host+0xDD3A50&&(void*)g_frame==(void*)Original);if(mode==17||mode==18)return MH_ERROR_MEMORY_PROTECT;enabled=1;return MH_OK;}
MH_STATUS WINAPI MH_RemoveHook(LPVOID p){event('D',0);CHECK(p==host+0xDD3A50);++removeCalls;if(hook==2)++foreignRemoved;if(mode==18)return MH_ERROR_MEMORY_PROTECT;hook=enabled=0;return MH_OK;}
MH_STATUS WINAPI MH_DisableHook(LPVOID p){(void)p;enabled=0;return MH_OK;}
'''
prefix += pending + "\nstatic Pending g_queue[DC_QUEUE_MAX];\nstatic HANDLE g_pipes[DC_PEERS+1];\n"
main = r'''
int main(void){
 host=(unsigned char*)calloc(1,0x37EC000);if(!host)return 2;IMAGE_DOS_HEADER* dos=(IMAGE_DOS_HEADER*)host;dos->e_magic=IMAGE_DOS_SIGNATURE;dos->e_lfanew=256;IMAGE_NT_HEADERS64* nt=(IMAGE_NT_HEADERS64*)(host+256);nt->OptionalHeader.SizeOfImage=0x37EC000;
 for(mode=0;mode<25;++mode){
  pipeCalls=eventCalls=threadCalls=openHelper=localLive=tokenLive=enabled=removeCalls=foreignRemoved=used=0;trace[0]=0;hook=mode==16?2:0;g_thread=mode==24?77:0;g_frame=NULL;g_started=1;g_hookInit=0;memset(pipes,0,sizeof(pipes));memset(events,0,sizeof(events));memset(g_pipes,0,sizeof(g_pipes));memset(g_queue,0,sizeof(g_queue));nt->FileHeader.TimeDateStamp=mode==1?0:0x6AA123BB;
  DWORD result=StartDebugService(NULL);int wanted=mode==1?6:mode==2?1:mode>=3&&mode<=5?2:mode==6?3:mode>=7&&mode<=9?4:mode>=10&&mode<=12?7:mode>=13&&mode<=18||mode==23?5:0;
  CHECK(result==wanted);CHECK(!localLive&&!tokenLive&&!foreignRemoved);
  if(wanted){for(int i=0;i<5;++i)CHECK(!pipes[i]);for(int i=0;i<32;++i)CHECK(!events[i]);CHECK(g_started==1);}
  else{CHECK(g_started==2&&threadCalls==5&&enabled&&hook==1&&(void*)g_frame==(void*)Original);CHECK(openHelper==(mode==19));}
  if(mode==16)CHECK(hook==2&&removeCalls==0);if(mode==17)CHECK(hook==0&&removeCalls==1);if(mode==18)CHECK(hook==1&&removeCalls==1);
  printf("case=%d result=%lu started=%ld pipe_calls=%d event_calls=%d peers=%d helper=%d hook=%d enabled=%d removed=%d foreign=%d trace=%s\n",mode,result,g_started,pipeCalls,eventCalls,threadCalls,openHelper,hook,enabled,removeCalls,foreignRemoved,trace);
 }
 printf("service_cases=25 checks=%d failed=%d;actual startup/adaptor,fake native APIs,no game\n",checks,failed);free(host);return failed?1:0;
}
'''
if "InlineHook_InstallInto" in (sdk / "hook/inline_hook.h").read_text(encoding="utf-8"):
    extra = r''' {void* slot=(void*)0xDEAD;int before=used;
    CHECK(!InlineHook_InstallInto(NULL,(void*)Frame,&slot));
    CHECK(!InlineHook_InstallInto(host+0xDD3A50,NULL,&slot));
    CHECK(!InlineHook_InstallInto(host+0xDD3A50,(void*)Frame,NULL));
    CHECK(slot==(void*)0xDEAD&&used==before);}
'''
    main = main.replace(' printf("service_cases=', extra + ' printf("service_cases=')
(output / "fixture.c").write_text(prefix + text[match.start():end] + "\n" + main, encoding="ascii")
vc = "C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat"
command = 'cmd /d /s /c "' + f'"{vc}" >nul && cl /nologo /W3 /TC /MT /I"{sdk / "minihook/include"}" /I"{root / "src/carrier"}" fixture.c /Fe:fixture.exe' + '"'
def run(command):
    p = subprocess.run(command, cwd=output, capture_output=True)
    return dict(command=command, cwd=str(output), stdout=p.stdout.decode("utf-8", errors="replace"), stderr=p.stderr.decode("utf-8", errors="replace"), exit=p.returncode)
build = run(command)
result = run([str(output / "fixture.exe")]) if build["exit"] == 0 else build
(output / "result.json").write_text(json.dumps(dict(build=build, result=result, scope="Actual StartDebugService and inline adapter;token,allocation,pipe,event,thread,MinHook modeled;checks trampoline published before Enable;no game hooks/peers started"), indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
raise SystemExit(result["exit"])
