import hashlib, json, pathlib, subprocess, sys

R = pathlib.Path(__file__).resolve().parents[3]
D = R / 'test/reports/20261012_variable64_transaction/console_wheel_host'
D.mkdir(parents=True, exist_ok=True)
phase = sys.argv[1]
source = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else R / 'src/debug_console/main.cpp'
text = source.read_text(encoding='utf-8')
mode = text.split('SetConsoleMode(g_in, ', 1)[1].split(');', 1)[0]
cpp = r'''
#define _WIN32_WINNT 0x0A00
#include <windows.h>
#include <cstdio>
#include <string>
#include <thread>
#include <vector>
static DWORD Mode(DWORD g_oldMode) { return %MODE_EXPRESSION%; }
int wmain(int argc, wchar_t**) {
 if(argc>1) {
  SetConsoleTitleW(L"HOI4 wheel host regression");
  HANDLE in=CreateFileW(L"CONIN$",GENERIC_READ|GENERIC_WRITE,FILE_SHARE_READ|FILE_SHARE_WRITE,NULL,OPEN_EXISTING,0,NULL);DWORD old=0,now=0;
  bool query=GetConsoleMode(in,&old)!=0;
  bool set=SetConsoleMode(in,Mode(old))!=0;
  bool read=GetConsoleMode(in,&now)!=0;
  bool host=query&&set&&read&&!(now&ENABLE_MOUSE_INPUT);
  bool keys=(now&(ENABLE_LINE_INPUT|ENABLE_ECHO_INPUT|ENABLE_PROCESSED_INPUT))==0;
  bool quick=(now&ENABLE_QUICK_EDIT_MODE)==0;
  bool window=(now&ENABLE_WINDOW_INPUT)!=0;
  bool all=true;for(unsigned n=0;n<256;++n){DWORD m=Mode(n);all &= !(m&ENABLE_MOUSE_INPUT)&&(m&ENABLE_EXTENDED_FLAGS)&&!(m&(ENABLE_LINE_INPUT|ENABLE_ECHO_INPUT|ENABLE_PROCESSED_INPUT|ENABLE_QUICK_EDIT_MODE));}
  printf("native_old_mode=%lu native_new_mode=%lu\n",old,now);
  printf("%s host_owns_mouse\n%s raw_keyboard\n%s quickedit_off\n%s resize_events\n%s 256_inherited_modes\n",host?"PASS":"FAIL",keys?"PASS":"FAIL",quick?"PASS":"FAIL",window?"PASS":"FAIL",all?"PASS":"FAIL");
  printf("%d/5\n",host+keys+quick+window+all);fflush(stdout);Sleep(200);return host&&keys&&quick&&window&&all?0:1;
 }
 HANDLE ir,iw,orr,ow; if(!CreatePipe(&ir,&iw,NULL,0)||!CreatePipe(&orr,&ow,NULL,0))return 2;
 HPCON pc;COORD size={80,25};HRESULT hr=CreatePseudoConsole(size,ir,ow,0,&pc);
 if(FAILED(hr)){printf("CreatePseudoConsole HRESULT=%lx\n",hr);return 2;}CloseHandle(ir);CloseHandle(ow);
 SIZE_T bytes=0;InitializeProcThreadAttributeList(NULL,1,0,&bytes);std::vector<char> attrs(bytes);
 STARTUPINFOEXW si={};si.StartupInfo.cb=sizeof(si);si.lpAttributeList=(LPPROC_THREAD_ATTRIBUTE_LIST)attrs.data();
 if(!InitializeProcThreadAttributeList(si.lpAttributeList,1,0,&bytes)||!UpdateProcThreadAttribute(si.lpAttributeList,0,PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE,pc,sizeof(pc),NULL,NULL))return 2;
 wchar_t self[32768];GetModuleFileNameW(NULL,self,32768);std::wstring cmd=L"\""+std::wstring(self)+L"\" --child";
 PROCESS_INFORMATION pi={};BOOL created=CreateProcessW(NULL,&cmd[0],NULL,NULL,FALSE,EXTENDED_STARTUPINFO_PRESENT,NULL,NULL,&si.StartupInfo,&pi);
 DeleteProcThreadAttributeList(si.lpAttributeList);if(!created){printf("CreateProcess error=%lu\n",GetLastError());ClosePseudoConsole(pc);return 2;}
 std::string output;std::thread reader([&]{char b[4096];DWORD n;while(ReadFile(orr,b,sizeof(b),&n,NULL)&&n)output.append(b,n);});
 DWORD wait=WaitForSingleObject(pi.hProcess,10000),code=2;if(wait==WAIT_OBJECT_0)GetExitCodeProcess(pi.hProcess,&code);else TerminateProcess(pi.hProcess,2);
 ClosePseudoConsole(pc);CloseHandle(iw);reader.join();CloseHandle(orr);CloseHandle(pi.hThread);CloseHandle(pi.hProcess);
 fwrite(output.data(),1,output.size(),stdout);bool noMouse=output.find("\x1b[?1003;1006h")==std::string::npos;
 printf("\n%s conpty_mouse_reporting_off\nnative_conpty_child_exit=%lu\n",noMouse?"PASS":"FAIL",code);return code==0&&noMouse?0:1;
}
'''.replace('%MODE_EXPRESSION%', mode)
p = D / f'{phase}_host.cpp'; p.write_text(cpp, encoding='utf-8')
exe = D / f'{phase}_host.exe'
vc = 'C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat'
cmd = f'"{vc}" >nul && cl /nologo /EHsc /std:c++17 /MT "{p}" /Fe:"{exe}" /Fo:"{D / (phase + ".obj")}"'
def run(c):
    p = subprocess.run(c, capture_output=True, timeout=40)
    return dict(command=c, stdout=p.stdout.decode('utf-8', errors='replace'), stderr=p.stderr.decode('utf-8', errors='replace'), exit=p.returncode)
build = run('cmd /d /s /c "' + cmd + '"')
result = run([str(exe)]) if build['exit'] == 0 else build
record = dict(phase=phase, source=str(source.resolve()), sha256=hashlib.sha256(source.read_bytes()).hexdigest(), exact_startup_expression=mode, build=build, result=result, scope='Real CreatePseudoConsole + child Get/SetConsoleMode using exact production startup expression; not physical wheel injection or GUI certification')
(D / f'{phase}.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
sys.stdout.reconfigure(encoding='utf-8', errors='replace');print(json.dumps(record, ensure_ascii=False, indent=2));sys.exit(result['exit'])
