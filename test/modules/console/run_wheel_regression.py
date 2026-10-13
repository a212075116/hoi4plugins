import hashlib, json, pathlib, subprocess, sys

R = pathlib.Path(__file__).resolve().parents[3]
D = R / 'test/reports/20261012_variable64_transaction/console_wheel'
D.mkdir(parents=True, exist_ok=True)
phase = sys.argv[1]
source = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else R / 'src/debug_console/main.cpp'
text = source.read_text(encoding='utf-8')
prefix = text.split('if (!ReadConsoleInputW(g_in, &rec, 1, &n)) break;', 1)[1].split('auto k = rec.Event.KeyEvent;', 1)[0]
harness = r'''
#include <windows.h>
#include <cstdio>
static CONSOLE_SCREEN_BUFFER_INFO screen;
static UINT lines = 3;
static bool infoOk = true, windowOk = true;
static BOOL WINAPI TestInfo(HANDLE, PCONSOLE_SCREEN_BUFFER_INFO p) { if (!infoOk) return FALSE; *p = screen; return TRUE; }
static BOOL WINAPI TestWindow(HANDLE, BOOL, const SMALL_RECT* p) { if (!windowOk) return FALSE; screen.srWindow = *p; return TRUE; }
static BOOL WINAPI TestSystem(UINT, UINT, PVOID p, UINT) { *(UINT*)p = lines; return TRUE; }
static BOOL WINAPI TestCursor(HANDLE, COORD p) {
 screen.dwCursorPosition = p;
 if(p.Y < screen.srWindow.Top || p.Y > screen.srWindow.Bottom) { int h=screen.srWindow.Bottom-screen.srWindow.Top; screen.srWindow.Top=(SHORT)(p.Y-h); screen.srWindow.Bottom=p.Y; }
 return TRUE;
}
static BOOL WINAPI TestWrite(HANDLE, const VOID* p, DWORD n, LPDWORD count, LPVOID) {
 const wchar_t* s=(const wchar_t*)p;
 for(DWORD i=0;i<n;++i) if(s[i]==L'\n') ++screen.dwCursorPosition.Y;
 TestCursor(NULL,screen.dwCursorPosition); *count=n; return TRUE;
}
#define GetConsoleScreenBufferInfo TestInfo
#define SetConsoleWindowInfo TestWindow
#define SystemParametersInfoW TestSystem
#define SetConsoleCursorPosition TestCursor
#define WriteConsoleW TestWrite
#define wmain OriginalMain
#include "SOURCE"
#undef wmain
static bool Replay(INPUT_RECORD rec) {
 for(int once=0;once<1;++once) { PREFIX return true; }
 return false;
}
static void Reset() { screen={};screen.dwSize={80,1000};screen.dwCursorPosition={2,900};screen.srWindow={0,881,79,900};g_console=true;g_edit=L"keep";g_cursor=2;lines=3;infoOk=windowOk=true; }
static void Wheel(int delta, DWORD flags=MOUSE_WHEELED) { INPUT_RECORD r={};r.EventType=MOUSE_EVENT;r.Event.MouseEvent.dwEventFlags=flags;r.Event.MouseEvent.dwButtonState=(DWORD)(WORD)(SHORT)delta<<16;Replay(r); }
int main() {
 int passed=0,total=0;
 auto check=[&](bool ok,const char* name){++total;passed+=ok;printf("%s %s\n",ok?"PASS":"FAIL",name);};
 Reset();Wheel(120);check(screen.srWindow.Top==878,"wheel_up_three_lines");
 Wheel(-120);check(screen.srWindow.Top==881,"wheel_down_three_lines");
 check(g_edit==L"keep"&&g_cursor==2&&screen.dwCursorPosition.Y==900,"input_and_cursor_unchanged");
 Reset();Wheel(60);check(screen.srWindow.Top==881,"partial_delta_no_full_notch");Wheel(60);check(screen.srWindow.Top==878,"partial_delta_accumulated");
 Reset();lines=WHEEL_PAGESCROLL;Wheel(120);check(screen.srWindow.Top==861,"page_scroll");
 Reset();lines=0;Wheel(120);check(screen.srWindow.Top==881,"system_scroll_disabled");
 Reset();Wheel(32760);check(screen.srWindow.Top==62,"large_positive_delta");Wheel(32760);check(screen.srWindow.Top==0,"clamp_top");Wheel(-32760);Wheel(-32760);check(screen.srWindow.Top==881,"clamp_history_bottom");
 Reset();Wheel(120,MOUSE_HWHEELED);check(screen.srWindow.Top==881,"horizontal_ignored");
 Reset();infoOk=false;Wheel(120);check(screen.srWindow.Top==881,"query_failure_safe");
 Reset();windowOk=false;Wheel(120);check(screen.srWindow.Top==881,"window_failure_safe");
 Reset();screen.srWindow.Top=800;screen.srWindow.Bottom=819;Print(L"new log");check(screen.srWindow.Top==800&&screen.srWindow.Bottom==819,"background_log_preserves_history_view");
 Reset();Print(L"new log");check(screen.srWindow.Bottom==901,"live_view_follows_output");
 Reset();INPUT_RECORD k={};k.EventType=KEY_EVENT;k.Event.KeyEvent.bKeyDown=TRUE;check(Replay(k),"keyboard_still_dispatched");
 Reset();unsigned seed=1234567;bool bounds=true;for(int i=0;i<100000;++i){seed=seed*1664525+1013904223;Wheel((seed&1)?120:-120);bounds &= screen.srWindow.Top>=0&&screen.srWindow.Bottom<=900&&screen.srWindow.Bottom-screen.srWindow.Top==19;}check(bounds,"100000_alternating_wheel_bounds");
 printf("%d/%d\n",passed,total);return passed==total?0:1;
}
'''.replace('SOURCE', source.resolve().as_posix()).replace('PREFIX', prefix)
catalog = source.resolve().parent / 'command_catalog.cpp'
if catalog.exists():
    harness += '\n#include "' + catalog.as_posix() + '"\n'
cpp = D / f'{phase}_harness.cpp'
exe = D / f'{phase}_harness.exe'
cpp.write_text(harness, encoding='utf-8')
vc = 'C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvars64.bat'
cmd = f'"{vc}" >nul && cl /nologo /EHsc /std:c++17 /MT "{cpp}" /Fe:"{exe}" /Fo:"{D / (phase + ".obj")}" shell32.lib user32.lib advapi32.lib'
def run(command):
    p = subprocess.run(command, capture_output=True)
    return dict(command=command, stdout=p.stdout.decode('utf-8', errors='replace'), stderr=p.stderr.decode('utf-8', errors='replace'), exit=p.returncode)
build = run('cmd /d /s /c "' + cmd + '"')
result = run([str(exe)]) if build['exit'] == 0 else build
record = dict(phase=phase, source=str(source.resolve()), sha256=hashlib.sha256(source.read_bytes()).hexdigest(), build=build, result=result, scope='Actual input-loop prefix and shared display functions; modeled Win32 viewport APIs, not physical mouse/GUI certification')
(D / f'{phase}.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
print(json.dumps(record, ensure_ascii=False, indent=2))
sys.exit(result['exit'])
