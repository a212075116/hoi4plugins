import argparse
import json
import pathlib
import subprocess


parser = argparse.ArgumentParser()
parser.add_argument("source_root", type=pathlib.Path)
parser.add_argument("output", type=pathlib.Path)
args = parser.parse_args()
root, output = args.source_root.resolve(), args.output.resolve()
output.mkdir(parents=True, exist_ok=True)
text = (root / "src/carrier/carrier_loader.cpp").read_text(encoding="utf-8")
start, end = text.index("static void LogPath("), text.index("static BYTE* g_image")
fixture = r'''
#include <windows.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
static int fault,opens,writes,closes,checks,failed;static char captured[4096],path[MAX_PATH];
static DWORD accessFlags,shareFlags;
static HANDLE WINAPI MockOpen(LPCSTR p,DWORD access,DWORD share,LPSECURITY_ATTRIBUTES sa,DWORD mode,DWORD flags,HANDLE parent){++opens;strcpy_s(path,sizeof(path),p);accessFlags=access;shareFlags=share;(void)sa;(void)mode;(void)flags;(void)parent;return fault==1?INVALID_HANDLE_VALUE:(HANDLE)0x55;}
static void WINAPI MockTime(LPSYSTEMTIME p){memset(p,0,sizeof(*p));p->wHour=1;p->wMinute=2;p->wSecond=3;p->wMilliseconds=4;}
static BOOL WINAPI MockWrite(HANDLE h,LPCVOID data,DWORD n,LPDWORD got,LPOVERLAPPED overlap){(void)h;(void)overlap;++writes;if(fault==2){*got=0;return FALSE;}*got=fault==3?n/2:n;memcpy(captured,data,*got);captured[*got]=0;return TRUE;}
static BOOL WINAPI MockClose(HANDLE h){(void)h;++closes;return TRUE;}
#define CreateFileA MockOpen
#define GetLocalTime MockTime
#define WriteFile MockWrite
#define CloseHandle MockClose
#include "CARRIER_HEADER"
#include "LOG_SOURCE"
LOG_FUNCTIONS
#define CHECK(x) do{++checks;if(!(x)){++failed;printf("FAIL line=%d\n",__LINE__);}}while(0)
static unsigned long long hash(const char* s){unsigned long long h=1469598103934665603ULL;while(*s)h=(h^(unsigned char)*s++)*1099511628211ULL;return h;}
int main(){
 const int sizes[]={0,1,16,2047,2048,4096};char message[4097];int cases=0;
 for(int size:sizes)for(fault=0;fault<4;++fault){
  memset(message,'x',size);message[size]=0;opens=writes=closes=0;captured[0]=path[0]=0;PLog("%s",message);
  CHECK(opens==(size<2048));CHECK(writes==(size<2048&&fault!=1));CHECK(closes==writes);
  if(opens)CHECK(accessFlags==FILE_APPEND_DATA&&shareFlags==(FILE_SHARE_READ|FILE_SHARE_WRITE)&&!strcmp(path,LOADER_LOG_DIR "/mod_loader_" CARRIER_LIBRARY ".log"));
  if(size<2048&&fault==0)CHECK(strlen(captured)==(size_t)size+17);
  printf("size=%d fault=%d opens=%d writes=%d closes=%d bytes=%zu hash=%llu path=%s\n",size,fault,opens,writes,closes,strlen(captured),hash(captured),path);++cases;
 }
 fault=0;opens=writes=closes=0;PLog("[info] %s %d","fixture",7);CHECK(!strcmp(captured,"[01:02:03.004] [info] fixture 7\r\n"));++cases;
 printf("carrier_log_cases=%d checks=%d failed=%d;actual PLog/backend,mocked file,time,no DLL loading\n",cases,checks,failed);return failed?1:0;
}
'''
fixture = fixture.replace("CARRIER_HEADER", (root / "src/carrier/carrier.h").as_posix()).replace("LOG_SOURCE", (root / "src/plugin/SDK_RVA/common/log.c").as_posix()).replace("LOG_FUNCTIONS", text[start:end])
(output / "fixture.cpp").write_text(fixture, encoding="ascii")
vc = "C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat"
command = 'cmd /d /s /c "' + f'"{vc}" >nul && cl /nologo /W4 /EHsc /std:c++17 /O2 fixture.cpp /Fe:fixture.exe' + '"'
def run(command):
    p = subprocess.run(command, cwd=output, capture_output=True)
    return dict(command=command, cwd=str(output), stdout=p.stdout.decode("utf-8", errors="replace"), stderr=p.stderr.decode("utf-8", errors="replace"), exit=p.returncode)
build = run(command)
result = run([str(output / "fixture.exe")]) if build["exit"] == 0 else build
(output / "result.json").write_text(json.dumps(dict(build=build, result=result, scope="Actual carrier logger and common backend; time/file operations controlled; no loader timing changed"), indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
raise SystemExit(result["exit"])
