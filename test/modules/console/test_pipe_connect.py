import argparse
import hashlib
import json
import pathlib
import subprocess


parser = argparse.ArgumentParser()
parser.add_argument("source_root", type=pathlib.Path)
parser.add_argument("output", type=pathlib.Path)
parser.add_argument("--real", action="store_true")
args = parser.parse_args()
root, output = args.source_root.resolve(), args.output.resolve()
output.mkdir(parents=True, exist_ok=True)
header = root / "src/debug_console/protocol.h"
source = root / "src/plugin/SDK_RVA/console/debug_console.c"
text = source.read_text(encoding="utf-8")
peer = text[text.index("static DWORD WINAPI Peer("):text.index("static void CloseStartupHandles(")]
if "BOOL connected = DcConnect(h);" in peer:
    connect = "static int TestConnect(HANDLE h){return DcConnect(h);}\n"
    assert "Sleep(50);" in peer and "ConnectNamedPipe(" not in peer
else:
    begin = peer.index("OVERLAPPED ov =")
    end = peer.index("        if (connected) {")
    connect = "static int TestConnect(HANDLE h){\n" + peer[begin:end] + "return connected;}\n"

fake = r'''
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>
static int mode,pending,alive,io,closes,cancels,drains,checks,failed,isConnect;
static DWORD error,amount;static OVERLAPPED* active;static ULONGLONG ticks;
#define CHECK(x) do{++checks;if(!(x)){++failed;printf("FAIL mode=%d line=%d\n",mode,__LINE__);}}while(0)
static HANDLE WINAPI Event(LPSECURITY_ATTRIBUTES p,BOOL manual,BOOL initial,LPCWSTR name){CHECK(!p&&manual&&!initial&&!name);if(mode==4)return NULL;alive=1;return (HANDLE)2;}
static BOOL WINAPI Close(HANDLE h){++closes;CHECK(h==(HANDLE)2&&alive&&!pending);alive=0;return h!=NULL;}
static DWORD WINAPI Error(void){return error;}
static ULONGLONG WINAPI Tick(void){return ticks++;}
static BOOL Begin(OVERLAPPED* ov,DWORD* n){++io;CHECK(alive&&ov->hEvent==(HANDLE)2);active=ov;if(mode==0){if(n)*n=amount;return TRUE;}if(mode==6){error=ERROR_ACCESS_DENIED;return FALSE;}pending=1;error=ERROR_IO_PENDING;return FALSE;}
static BOOL WINAPI Connect(HANDLE h,LPOVERLAPPED ov){CHECK(h==(HANDLE)1);if(mode==1){++io;CHECK(alive);error=ERROR_PIPE_CONNECTED;return FALSE;}return Begin(ov,NULL);}
static BOOL WINAPI Read(HANDLE h,LPVOID data,DWORD n,LPDWORD out,LPOVERLAPPED ov){CHECK(h==(HANDLE)1&&data&&n);amount=n>16?16:n;return Begin(ov,out);}
static BOOL WINAPI Write(HANDLE h,LPCVOID data,DWORD n,LPDWORD out,LPOVERLAPPED ov){return Read(h,(void*)data,n,out,ov);}
static DWORD WINAPI Wait(HANDLE h,DWORD timeout){CHECK(h==(HANDLE)2&&alive&&pending&&(timeout==INFINITE||timeout<30000));return mode==3||mode==8||mode==4?WAIT_FAILED:mode==5?WAIT_TIMEOUT:WAIT_OBJECT_0;}
static DWORD WINAPI Multi(DWORD n,const HANDLE* handles,BOOL all,DWORD timeout){CHECK(n==2&&handles[0]==(HANDLE)2&&handles[1]==(HANDLE)3&&!all);return Wait(handles[0],timeout);}
static BOOL WINAPI Cancel(HANDLE h,LPOVERLAPPED ov){++cancels;CHECK(h==(HANDLE)1&&ov==active&&pending);if(mode==8){error=ERROR_NOT_FOUND;return FALSE;}return TRUE;}
static BOOL WINAPI Result(HANDLE h,LPOVERLAPPED ov,LPDWORD n,BOOL wait){CHECK(h==(HANDLE)1&&ov==active);if(wait){++drains;pending=0;*n=amount;return TRUE;}if(mode==3||mode==4||mode==5||mode==8||mode==9){error=ERROR_IO_INCOMPLETE;return FALSE;}pending=0;*n=amount;if(mode==7){error=ERROR_OPERATION_ABORTED;return FALSE;}return TRUE;}
#define CreateEventW Event
#define CloseHandle Close
#define GetLastError Error
#define GetTickCount64 Tick
#define ConnectNamedPipe Connect
#define ReadFile Read
#define WriteFile Write
#define WaitForSingleObject Wait
#define WaitForMultipleObjects Multi
#define CancelIoEx Cancel
#define GetOverlappedResult Result
@@HEADER@@
@@CONNECT@@
static void reset(void){pending=alive=io=closes=cancels=drains=0;ticks=0;active=NULL;amount=0;error=0;}
int main(void){
 char payload[64]={0};int connectCases=0,transferCases=0;
 for(int round=0;round<100;++round)for(mode=0;mode<10;++mode){reset();isConnect=1;int ok=TestConnect((HANDLE)1);CHECK(ok==(mode==0||mode==1||mode==2));CHECK(!pending&&!alive);if(mode==4)CHECK(!io&&!closes&&!cancels&&!drains);++connectCases;}
 for(int round=0;round<50;++round)for(mode=0;mode<10;++mode)for(int writing=0;writing<2;++writing)for(int cancel=0;cancel<2;++cancel){
  reset();isConnect=0;int ok=DcTransferWithCancel((HANDLE)1,payload,64,writing,30000,cancel?(HANDLE)3:NULL);
  CHECK(ok==(mode==0||mode==1||mode==2));CHECK(!pending&&!alive);if(mode==4)CHECK(!io&&!closes);++transferCases;
 }
 printf("connect_cases=%d transfer_cases=%d checks=%d failed=%d;actual connection andprotocol,controlled native API,event allocation/wait/error/cancel race/incomplete completion\n",connectCases,transferCases,checks,failed);return failed?1:0;
}
'''
real = r'''
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>
@@HEADER@@
@@CONNECT@@
static volatile LONG checks,failed;
#define CHECK(x) do{InterlockedIncrement(&checks);if(!(x)){InterlockedIncrement(&failed);printf("FAIL line=%d\n",__LINE__);}}while(0)
typedef struct{wchar_t name[128];HANDLE opened;int delayed;}Client;
static DWORD WINAPI Exchange(LPVOID value){Client* c=(Client*)value;if(c->delayed)Sleep(10);HANDLE h=CreateFileW(c->name,GENERIC_READ|GENERIC_WRITE,0,NULL,OPEN_EXISTING,0,NULL);CHECK(h!=INVALID_HANDLE_VALUE);if(h==INVALID_HANDLE_VALUE)return 1;CHECK(SetEvent(c->opened));char data[4];DWORD n;CHECK(WriteFile(h,"PING",4,&n,NULL)&&n==4);CHECK(ReadFile(h,data,4,&n,NULL)&&n==4&&!memcmp(data,"PONG",4));CHECK(CloseHandle(h));return 0;}
int main(void){DWORD original,after;GetProcessHandleCount(GetCurrentProcess(),&original);
 for(int i=0;i<64;++i){Client c;char data[4];c.delayed=i%2;_snwprintf_s(c.name,128,_TRUNCATE,L"\\\\.\\pipe\\hoi4-connect-fixture-%lu-%d",GetCurrentProcessId(),i);c.opened=CreateEventW(NULL,TRUE,FALSE,NULL);CHECK(c.opened!=NULL);
  HANDLE h=CreateNamedPipeW(c.name,PIPE_ACCESS_DUPLEX|FILE_FLAG_OVERLAPPED,PIPE_TYPE_BYTE|PIPE_READMODE_BYTE|PIPE_WAIT,1,64,64,0,NULL);CHECK(h!=INVALID_HANDLE_VALUE);HANDLE thread=CreateThread(NULL,0,Exchange,&c,0,NULL);CHECK(thread!=NULL);
  if(!c.delayed)CHECK(WaitForSingleObject(c.opened,5000)==WAIT_OBJECT_0);
  CHECK(TestConnect(h));CHECK(DcTransfer(h,data,4,0,5000)&&!memcmp(data,"PING",4));CHECK(DcTransfer(h,"PONG",4,1,5000));CHECK(WaitForSingleObject(thread,5000)==WAIT_OBJECT_0);CHECK(DisconnectNamedPipe(h));CHECK(CloseHandle(h));CHECK(CloseHandle(thread));CHECK(CloseHandle(c.opened));GetProcessHandleCount(GetCurrentProcess(),&after);CHECK(after==original);
 }
 printf("real_pipe_exchanges=64 preconnected=32 delayed=32 checks=%ld failed=%ld;actual protocol andconnection,real Win32 pipes/threads/payloads,owned handles restored\n",checks,failed);return failed?1:0;
}
'''
fixture = (real if args.real else fake).replace("@@HEADER@@", f'#include "{header.as_posix()}"').replace("@@CONNECT@@", connect)
(output / "fixture.c").write_text(fixture, encoding="ascii")
vc = "C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat"
command = 'cmd /d /s /c "' + f'"{vc}" >nul && cl /nologo /W3 /TC /MT /O2 fixture.c /Fe:fixture.exe' + '"'


def run(cmd):
    p = subprocess.run(cmd, cwd=output, capture_output=True)
    return dict(command=cmd, cwd=str(output), stdout=p.stdout.decode("utf-8", errors="replace"),
                stderr=p.stderr.decode("utf-8", errors="replace"), exit=p.returncode)


build = run(command)
result = run([str(output / "fixture.exe")]) if build["exit"] == 0 else build
inputs = "real64 alternating preconnected/delayed PING-PONG" if args.real else "connect10*100;transfer10*2write*2cancel*50"
(output / "result.json").write_text(json.dumps(dict(build=build, result=result,
    input_sha256=hashlib.sha256(inputs.encode()).hexdigest(),
    source_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in [header, source]},
    scope="Actual protocol and connection block; " + ("real local Win32 transport; no game permissions/queue" if args.real else "native dependencies controlled; pending lifetime asserted")), indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
raise SystemExit(result["exit"])
