import argparse
import hashlib
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
source = root / "src/plugin/SDK_RVA/console/debug_console.c"
text = source.read_text(encoding="utf-8")


def actual(name):
    found = re.search(r"^(?:static )?[^\n]+ " + name + r"\([^;]+?\{", text, re.M)
    if not found:
        raise ValueError("Missing actual gate function: " + name)
    end, depth = found.end(), 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[found.start():end] + "\n"


fixture = r'''
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#define DC_PEERS 4
static volatile LONG g_peerState,g_started,peerCalls,serviceCalls;
static HANDLE g_pipes[5],monitors[5];
static unsigned mask,threadCalls,closes;
static volatile LONG checks,failed;
#define CHECK(x) do{InterlockedIncrement(&checks);if(!(x)){InterlockedIncrement(&failed);printf("FAIL mask=%u line=%d\n",mask,__LINE__);}}while(0)
static DWORD WINAPI Peer(LPVOID p){CHECK((size_t)p>=0x100&&(size_t)p<0x105&&g_started==2&&g_peerState==1);InterlockedIncrement(&peerCalls);return 0;}
static DWORD WINAPI StartDebugService(LPVOID p){(void)p;InterlockedIncrement(&serviceCalls);return 0;}
void Plugin_Log(const char* fmt,...){(void)fmt;}
static HANDLE WINAPI NewThread(LPSECURITY_ATTRIBUTES sa,SIZE_T stack,LPTHREAD_START_ROUTINE fn,LPVOID arg,DWORD flags,LPDWORD id){
 unsigned i=threadCalls++;CHECK(i<5&&!flags);if(mask&(1u<<i)){SetLastError(ERROR_NOT_ENOUGH_MEMORY);return NULL;}
 HANDLE h=CreateThread(sa,stack,fn,arg,flags,id);CHECK(h!=NULL);
 if(h)CHECK(DuplicateHandle(GetCurrentProcess(),h,GetCurrentProcess(),&monitors[i],SYNCHRONIZE,FALSE,0));return h;
}
static BOOL WINAPI CloseOwned(HANDLE h){BOOL ok=CloseHandle(h);CHECK(ok);++closes;return ok;}
#define CreateThread NewThread
#define CloseHandle CloseOwned
ACTUAL
#undef CreateThread
#undef CloseHandle
int main(void){
 DWORD original,after;GetProcessHandleCount(GetCurrentProcess(),&original);
 for(unsigned round=0;round<16;++round)for(mask=0;mask<32;++mask){
  threadCalls=closes=0;peerCalls=0;g_peerState=0;g_started=1;ZeroMemory(monitors,sizeof(monitors));
  for(unsigned i=0;i<5;++i)g_pipes[i]=(HANDLE)(size_t)(0x100+i);
  int result=StartPeerThreads();CHECK(result==(mask==0));CHECK(peerCalls==0);
  if(!mask){Sleep(2);CHECK(peerCalls==0&&g_peerState==0);InterlockedExchange(&g_started,2);InterlockedExchange(&g_peerState,1);}
  else CHECK(g_peerState==-1);
  unsigned live=0;for(unsigned i=0;i<5;++i)if(monitors[i]){++live;CHECK(WaitForSingleObject(monitors[i],5000)==WAIT_OBJECT_0);CHECK(CloseHandle(monitors[i]));}
  CHECK(closes==live);CHECK(peerCalls==(!mask?5:0));GetProcessHandleCount(GetCurrentProcess(),&after);CHECK(after==original);
 }
 mask=1;threadCalls=0;g_started=0;serviceCalls=0;DebugConsole_Start();CHECK(g_started==-1&&threadCalls==1&&serviceCalls==0);DebugConsole_Start();CHECK(threadCalls==1);
 GetProcessHandleCount(GetCurrentProcess(),&after);CHECK(after==original);
 printf("real_gate_cases=512 launcher_failure=1 checks=%ld failed=%ld;actual gate/launcher,real Win32 threads,all32 failure masks,no peers before commit,no retained handles\n",checks,failed);return failed?1:0;
}
'''
fixture = fixture.replace("ACTUAL", "".join(actual(n) for n in ["PeerStart", "StartPeerThreads", "DebugConsole_Start"]))
(output / "fixture.c").write_text(fixture, encoding="ascii")
vc = "C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat"
command = 'cmd /d /s /c "' + f'"{vc}" >nul && cl /nologo /W3 /TC /MT /O2 fixture.c /Fe:fixture.exe' + '"'


def run(cmd):
    p = subprocess.run(cmd, cwd=output, capture_output=True)
    return dict(command=cmd, cwd=str(output), stdout=p.stdout.decode("utf-8", errors="replace"),
                stderr=p.stderr.decode("utf-8", errors="replace"), exit=p.returncode)


build = run(command)
result = run([str(output / "fixture.exe")]) if build["exit"] == 0 else build
(output / "result.json").write_text(json.dumps(dict(build=build, result=result,
    source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    scope="Actual gate,peer thread creation and launcher; real Win32 threads/handles; Peer body controlled; no game dispatch"), indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
raise SystemExit(result["exit"])
