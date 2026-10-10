#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <string.h>

#include "process_block.h"
#include "inline_hook.h"
#include "hook_guard.h"

extern void Plugin_Log(const char* fmt, ...);

__declspec(thread) int g_hookReentry = 0;

typedef BOOL (WINAPI *CreateProcessAFn)(LPCSTR, LPSTR, LPSECURITY_ATTRIBUTES,
                                        LPSECURITY_ATTRIBUTES, BOOL, DWORD, LPVOID,
                                        LPCSTR, LPSTARTUPINFOA, LPPROCESS_INFORMATION);
typedef BOOL (WINAPI *CreateProcessWFn)(LPCWSTR, LPWSTR, LPSECURITY_ATTRIBUTES,
                                        LPSECURITY_ATTRIBUTES, BOOL, DWORD, LPVOID,
                                        LPCWSTR, LPSTARTUPINFOW, LPPROCESS_INFORMATION);

static CreateProcessAFn g_origA = NULL;
static CreateProcessWFn g_origW = NULL;
static int g_installed = 0;
static int g_enabled = 1;
static int g_blocked = 0;

static int EqNoCase(char a, char b)
{
    if (a >= 'A' && a <= 'Z') a = (char)(a - 'A' + 'a');
    if (b >= 'A' && b <= 'Z') b = (char)(b - 'A' + 'a');
    return a == b;
}

static int ContainsNoCaseA(const char* hay, const char* needle)
{
    size_t i;
    if (hay == NULL || needle == NULL) return 0;
    if (needle[0] == 0) return 1;
    for (i = 0; hay[i] != 0; ++i) {
        size_t j = 0;
        while (needle[j] != 0 && hay[i + j] != 0 && EqNoCase(hay[i + j], needle[j])) ++j;
        if (needle[j] == 0) return 1;
    }
    return 0;
}

static int ContainsNoCaseW(const WCHAR* hay, const WCHAR* needle)
{
    size_t i;
    if (hay == NULL || needle == NULL) return 0;
    if (needle[0] == 0) return 1;
    for (i = 0; hay[i] != 0; ++i) {
        size_t j = 0;
        while (needle[j] != 0 && hay[i + j] != 0) {
            WCHAR a = hay[i + j];
            WCHAR b = needle[j];
            if (a >= 'A' && a <= 'Z') a = (WCHAR)(a - 'A' + 'a');
            if (b >= 'A' && b <= 'Z') b = (WCHAR)(b - 'A' + 'a');
            if (a != b) break;
            ++j;
        }
        if (needle[j] == 0) return 1;
    }
    return 0;
}

static int ShouldBlockA(const char* app, const char* cmd)
{
    const char* s = (cmd != NULL && cmd[0] != 0) ? cmd : app;
    if (s == NULL || s[0] == 0) return 0;
    if (!ContainsNoCaseA(s, "notepad")) return 0;
    if (!ContainsNoCaseA(s, ".log")) return 0;
    return 1;
}

static int ShouldBlockW(const WCHAR* app, const WCHAR* cmd)
{
    const WCHAR* s = (cmd != NULL && cmd[0] != 0) ? cmd : app;
    if (s == NULL || s[0] == 0) return 0;
    if (!ContainsNoCaseW(s, L"notepad")) return 0;
    if (!ContainsNoCaseW(s, L".log")) return 0;
    return 1;
}

static void ClearProcessInfo(LPPROCESS_INFORMATION pi)
{
    if (pi == NULL) return;
    pi->hProcess = NULL;
    pi->hThread = NULL;
    pi->dwProcessId = 0;
    pi->dwThreadId = 0;
}

static BOOL WINAPI Hook_CreateProcessA(LPCSTR app, LPSTR cmd, LPSECURITY_ATTRIBUTES pa,
                                       LPSECURITY_ATTRIBUTES ta, BOOL inherit, DWORD flags,
                                       LPVOID env, LPCSTR cwd, LPSTARTUPINFOA si,
                                       LPPROCESS_INFORMATION pi)
{
    int hit;
    if (g_hookReentry > 0) {
        return g_origA(app, cmd, pa, ta, inherit, flags, env, cwd, si, pi);
    }
    ++g_hookReentry;
    hit = (g_enabled && ShouldBlockA(app, cmd));
    if (hit) {
        ++g_blocked;
        Plugin_Log("[pblock] blocked #%d A: %s", g_blocked, cmd != NULL ? cmd : "(null)");
        ClearProcessInfo(pi);
        SetLastError(ERROR_ACCESS_DENIED);
    }
    --g_hookReentry;
    if (hit) return FALSE;
    return g_origA(app, cmd, pa, ta, inherit, flags, env, cwd, si, pi);
}

static BOOL WINAPI Hook_CreateProcessW(LPCWSTR app, LPWSTR cmd, LPSECURITY_ATTRIBUTES pa,
                                       LPSECURITY_ATTRIBUTES ta, BOOL inherit, DWORD flags,
                                       LPVOID env, LPCWSTR cwd, LPSTARTUPINFOW si,
                                       LPPROCESS_INFORMATION pi)
{
    int hit;
    if (g_hookReentry > 0) {
        return g_origW(app, cmd, pa, ta, inherit, flags, env, cwd, si, pi);
    }
    ++g_hookReentry;
    hit = (g_enabled && ShouldBlockW(app, cmd));
    if (hit) {
        ++g_blocked;
        Plugin_Log("[pblock] blocked #%d W", g_blocked);
        ClearProcessInfo(pi);
        SetLastError(ERROR_ACCESS_DENIED);
    }
    --g_hookReentry;
    if (hit) return FALSE;
    return g_origW(app, cmd, pa, ta, inherit, flags, env, cwd, si, pi);
}

static void* ApiTarget(const WCHAR* module, const char* name)
{
    HMODULE hm = GetModuleHandleW(module);
    if (hm == NULL) return NULL;
    return (void*)GetProcAddress(hm, name);
}

int ProcBlock_Install(void)
{
    void* t1;
    void* t2;
    if (g_installed) return 1;

    t1 = ApiTarget(L"kernel32.dll", "CreateProcessA");
    t2 = ApiTarget(L"kernel32.dll", "CreateProcessW");
    if (t1 == NULL && t2 == NULL) {
        Plugin_Log("[pblock] no CreateProcess found");
        return 0;
    }

    if (t1 != NULL) {
        g_origA = (CreateProcessAFn)InlineHook_Install(t1, (void*)Hook_CreateProcessA);
    }
    if (t2 != NULL) {
        g_origW = (CreateProcessWFn)InlineHook_Install(t2, (void*)Hook_CreateProcessW);
    }
    if (g_origA == NULL && g_origW == NULL) {
        Plugin_Log("[pblock] install failed");
        return 0;
    }

    g_installed = 1;
    Plugin_Log("[pblock] installed via MinHook A=%p W=%p origA=%p origW=%p",
               t1, t2, (void*)g_origA, (void*)g_origW);
    return 1;
}

int ProcBlock_Installed(void) { return g_installed; }
int ProcBlock_BlockedCount(void) { return g_blocked; }
void ProcBlock_SetEnabled(int on) { g_enabled = on ? 1 : 0; }
int ProcBlock_Enabled(void) { return g_enabled; }
