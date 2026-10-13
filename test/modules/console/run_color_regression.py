import hashlib,json,pathlib,subprocess,sys
R=pathlib.Path(__file__).resolve().parents[3];D=R/'test/reports/20261012_variable64_transaction/console_colors';D.mkdir(exist_ok=True)
phase=sys.argv[1];source=pathlib.Path(sys.argv[2]) if len(sys.argv)>2 else R/'src/debug_console/main.cpp'
cpp=r'''
#define _WIN32_WINNT 0x0a00
#include <windows.h>
#include <cstdio>
#include <string>
#include <vector>
#include <thread>
static bool native=false,failColor=false;
static CONSOLE_SCREEN_BUFFER_INFO screen;
static WORD active=0x17;
static std::vector<std::pair<std::wstring,WORD>> writes;
static BOOL WINAPI Info(HANDLE h,PCONSOLE_SCREEN_BUFFER_INFO p){if(native)return GetConsoleScreenBufferInfo(h,p);*p=screen;p->wAttributes=active;return TRUE;}
static BOOL WINAPI Color(HANDLE h,WORD a){if(failColor)return FALSE;if(native)return SetConsoleTextAttribute(h,a);active=a;return TRUE;}
static BOOL WINAPI Cursor(HANDLE h,COORD p){if(native)return SetConsoleCursorPosition(h,p);screen.dwCursorPosition=p;return TRUE;}
static BOOL WINAPI Window(HANDLE h,BOOL a,const SMALL_RECT* r){if(native)return SetConsoleWindowInfo(h,a,r);screen.srWindow=*r;return TRUE;}
static BOOL WINAPI Output(HANDLE h,const VOID* p,DWORD n,LPDWORD count,LPVOID r){if(native)return WriteConsoleW(h,p,n,count,r);writes.emplace_back(std::wstring((const wchar_t*)p,n),active);for(DWORD i=0;i<n;i++)if(((const wchar_t*)p)[i]==L'\n')++screen.dwCursorPosition.Y;*count=n;return TRUE;}
#define GetConsoleScreenBufferInfo Info
#define SetConsoleTextAttribute Color
#define SetConsoleCursorPosition Cursor
#define SetConsoleWindowInfo Window
#define WriteConsoleW Output
#define wmain OriginalMain
#include "SOURCE"
#undef wmain
static void Reset(){failColor=false;active=0x17;writes.clear();screen={};screen.dwSize={80,60};screen.srWindow={0,0,79,29};g_console=true;g_edit=L"";g_cursor=0;if(native){Color(g_out,0x17);Cursor(g_out,{0,0});DWORD n;FillConsoleOutputCharacterW(g_out,L' ',4800,{0,0},&n);}}
static bool Row(const std::wstring& text,WORD want,int y=0){
 if(native){CHAR_INFO cells[80];SMALL_RECT row={0,(SHORT)y,79,(SHORT)y};if(!ReadConsoleOutputW(g_out,cells,{80,1},{0,0},&row))return false;std::wstring s;for(int j=0;j<80&&s.size()<text.size();j++){if((cells[j].Attributes&0xff)!=(want&0xff))return false;if(!(cells[j].Attributes&COMMON_LVB_TRAILING_BYTE))s+=cells[j].Char.UnicodeChar;}return s==text;}
 for(auto& w:writes)if(w.first.find(text)!=std::wstring::npos)return w.second==want;return false;
}
static int Tests(){
 if(native){g_out=CreateConsoleScreenBuffer(GENERIC_READ|GENERIC_WRITE,FILE_SHARE_READ|FILE_SHARE_WRITE,NULL,CONSOLE_TEXTMODE_BUFFER,NULL);if(g_out==INVALID_HANDLE_VALUE)return 2;}
 int passed=0,total=0;auto check=[&](bool good,const char* name){++total;passed+=good;printf("%s %s\n",good?"PASS":"FAIL",name);};
 struct Case{const wchar_t* text;WORD fg;const char* name;};
 Case cases[]={{L"[GAME] prefix [error] entire line",12,"error_whole_line"},{L"[ErRoR] case",12,"case_insensitive"},{L"[warning] warning",14,"warning_yellow"},{L"[waring] typo",14,"waring_yellow"},{L"[WARN] short",14,"warn_yellow"},{L"[fatal] fatal",12,"fatal_red"},{L"[info] info",11,"info_cyan"},{L"[success] success",10,"success_green"},{L"[debug] debug",8,"debug_gray"},{L"[trace] trace",8,"trace_gray"},{L"plain unchanged",7,"untagged_normal"},{L"[warning] [error] mixed",12,"error_priority"},{L"error without bracket",7,"no_substring_false_positive"},{L"[error] \u4e2d\u6587\u65e5\u5fd7",12,"unicode_preserved"}};
 for(const auto& c:cases){Reset();Print(c.text);check(Row(c.text,(WORD)(0x10|c.fg)),c.name);}
 CONSOLE_SCREEN_BUFFER_INFO after;Info(g_out,&after);check(after.wAttributes==0x17,"restore_prompt_and_background");
 Reset();Print(L"[error] first\n[warning] second");check(Row(L"[error] first",0x1c,0)&&Row(L"[warning] second",0x1e,1),"multiline_separate_colors");
 Reset();failColor=true;Print(L"[error] fallback");check(Row(L"[error] fallback",0x17),"color_api_failure_plain");
 Reset();g_console=false;Print(L"[error] redirected_plain");check(active==0x17,"redirect_no_color_state");
 Reset();bool bounded=true;for(int i=0;i<(native?100:10000);i++){Print(L"[warning] burst");Info(g_out,&after);bounded &= after.wAttributes==0x17;writes.clear();}check(bounded,native?"100_native_lines_restore_state":"10000_model_lines_restore_state");
 printf("%d/%d mode=%s\n",passed,total,native?"native_private_console_buffer":"api_model");if(native)CloseHandle(g_out);return passed==total?0:1;
}
int wmain(int argc,wchar_t** argv){
 if(argc>1&&wcscmp(argv[1],L"--child")==0){native=true;return Tests();}
 if(argc==1)return Tests();
 HANDLE ir,iw,orr,ow;CreatePipe(&ir,&iw,NULL,0);CreatePipe(&orr,&ow,NULL,0);HPCON pc;COORD size={80,30};if(FAILED(CreatePseudoConsole(size,ir,ow,0,&pc)))return 2;CloseHandle(ir);CloseHandle(ow);
 SIZE_T n=0;InitializeProcThreadAttributeList(NULL,1,0,&n);std::vector<char> a(n);STARTUPINFOEXW si={};si.StartupInfo.cb=sizeof(si);si.lpAttributeList=(LPPROC_THREAD_ATTRIBUTE_LIST)a.data();InitializeProcThreadAttributeList(si.lpAttributeList,1,0,&n);UpdateProcThreadAttribute(si.lpAttributeList,0,PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE,pc,sizeof(pc),NULL,NULL);
 wchar_t self[32768];GetModuleFileNameW(NULL,self,32768);std::wstring cmd=L"\""+std::wstring(self)+L"\" --child";PROCESS_INFORMATION pi={};if(!CreateProcessW(NULL,&cmd[0],NULL,NULL,FALSE,EXTENDED_STARTUPINFO_PRESENT,NULL,NULL,&si.StartupInfo,&pi))return 2;DeleteProcThreadAttributeList(si.lpAttributeList);
 std::string text;std::thread reader([&]{char b[4096];DWORD m;while(ReadFile(orr,b,sizeof(b),&m,NULL)&&m)text.append(b,m);});WaitForSingleObject(pi.hProcess,30000);DWORD code=2;GetExitCodeProcess(pi.hProcess,&code);ClosePseudoConsole(pc);CloseHandle(iw);reader.join();CloseHandle(orr);CloseHandle(pi.hThread);CloseHandle(pi.hProcess);fwrite(text.data(),1,text.size(),stdout);return (int)code;
}
'''.replace('SOURCE',source.resolve().as_posix())
catalog=source.resolve().parent/'command_catalog.cpp'
if catalog.exists():cpp += '\n#include "'+catalog.as_posix()+'"\n'
p=D/(phase+'_color.cpp');p.write_text(cpp,encoding='utf-8');exe=D/(phase+'_color.exe');vc='C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat'
cmd=f'"{vc}" >nul && cl /nologo /EHsc /std:c++17 /MT "{p}" /Fe:"{exe}" /Fo:"{D/(phase+".obj")}" user32.lib shell32.lib advapi32.lib'
def run(c):
 p=subprocess.run(c,capture_output=True,timeout=60);return dict(command=c,stdout=p.stdout.decode('utf-8',errors='replace'),stderr=p.stderr.decode('utf-8',errors='replace'),exit=p.returncode)
build=run('cmd /d /s /c "'+cmd+'"');model=run([str(exe)]) if not build['exit'] else build;real=run([str(exe),'--native']) if not build['exit'] else build
x=dict(phase=phase,source=str(source.resolve()),sha256=hashlib.sha256(source.read_bytes()).hexdigest(),build=build,model=model,native=real,scope='Real Print, modeled API checks and real ConPTY private screen-buffer character attributes; not GUI screenshot or theme certification')
(D/(phase+'.json')).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8');sys.stdout.reconfigure(encoding='utf-8');print(json.dumps(x,ensure_ascii=False,indent=2));sys.exit(int(model['exit']!=0 or real['exit']!=0))
