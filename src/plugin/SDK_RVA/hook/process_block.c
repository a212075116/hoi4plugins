#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <string.h>

#include "process_block.h"

extern void Plugin_Log(const char* fmt, ...);

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

static unsigned char* Img(void)
{
    return (unsigned char*)GetModuleHandleA(NULL);
}

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
    if (g_enabled && ShouldBlockA(app, cmd)) {
        ++g_blocked;
        Plugin_Log("[pblock] blocked #%d A: %s", g_blocked, cmd != NULL ? cmd : "(null)");
        ClearProcessInfo(pi);
        SetLastError(ERROR_ACCESS_DENIED);
        return FALSE;
    }
    return g_origA(app, cmd, pa, ta, inherit, flags, env, cwd, si, pi);
}

static BOOL WINAPI Hook_CreateProcessW(LPCWSTR app, LPWSTR cmd, LPSECURITY_ATTRIBUTES pa,
                                       LPSECURITY_ATTRIBUTES ta, BOOL inherit, DWORD flags,
                                       LPVOID env, LPCWSTR cwd, LPSTARTUPINFOW si,
                                       LPPROCESS_INFORMATION pi)
{
    if (g_enabled && ShouldBlockW(app, cmd)) {
        ++g_blocked;
        Plugin_Log("[pblock] blocked #%d W", g_blocked);
        ClearProcessInfo(pi);
        SetLastError(ERROR_ACCESS_DENIED);
        return FALSE;
    }
    return g_origW(app, cmd, pa, ta, inherit, flags, env, cwd, si, pi);
}

static void** FindIatSlot(const char* moduleName, const char* funcName)
{
    unsigned char* img = Img();
    IMAGE_DOS_HEADER* dos;
    IMAGE_NT_HEADERS* nt;
    IMAGE_IMPORT_DESCRIPTOR* imp;
    DWORD impRva;

    if (img == NULL) return NULL;
    dos = (IMAGE_DOS_HEADER*)img;
    if (dos->e_magic != IMAGE_DOS_SIGNATURE) return NULL;
    nt = (IMAGE_NT_HEADERS*)(img + dos->e_lfanew);
    if (nt->Signature != IMAGE_NT_SIGNATURE) return NULL;

    impRva = nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT].VirtualAddress;
    if (impRva == 0) return NULL;
    imp = (IMAGE_IMPORT_DESCRIPTOR*)(img + impRva);

    while (imp->Name != 0) {
        const char* dll = (const char*)(img + imp->Name);
        if (ContainsNoCaseA(dll, moduleName)) {
            IMAGE_THUNK_DATA* oft = (IMAGE_THUNK_DATA*)(img + imp->OriginalFirstThunk);
            IMAGE_THUNK_DATA* ft = (IMAGE_THUNK_DATA*)(img + imp->FirstThunk);
            int i = 0;
            if (imp->OriginalFirstThunk == 0) { ++imp; continue; }
            while (oft[i].u1.AddressOfData != 0) {
                if ((oft[i].u1.Ordinal & IMAGE_ORDINAL_FLAG64) == 0) {
                    IMAGE_IMPORT_BY_NAME* ibn =
                        (IMAGE_IMPORT_BY_NAME*)(img + oft[i].u1.AddressOfData);
                    if (strcmp((const char*)ibn->Name, funcName) == 0) {
                        return (void**)&ft[i].u1.Function;
                    }
                }
                ++i;
            }
        }
        ++imp;
    }
    return NULL;
}

static int PatchSlot(void** slot, void* fn)
{
    DWORD old = 0;
    if (slot == NULL) return 0;
    if (!VirtualProtect(slot, sizeof(void*), PAGE_READWRITE, &old)) return 0;
    *slot = fn;
    VirtualProtect(slot, sizeof(void*), old, &old);
    return 1;
}

int ProcBlock_Install(void)
{
    void** s1;
    void** s2;
    if (g_installed) return 1;

    s1 = FindIatSlot("kernel32", "CreateProcessA");
    s2 = FindIatSlot("kernel32", "CreateProcessW");
    if (s1 == NULL && s2 == NULL) {
        Plugin_Log("[pblock] no CreateProcess IAT slot found");
        return 0;
    }

    if (s1 != NULL) g_origA = (CreateProcessAFn)(*s1);
    if (s2 != NULL) g_origW = (CreateProcessWFn)(*s2);

    if (s1 != NULL) PatchSlot(s1, (void*)Hook_CreateProcessA);
    if (s2 != NULL) PatchSlot(s2, (void*)Hook_CreateProcessW);

    g_installed = 1;
    Plugin_Log("[pblock] installed A=%p W=%p", (void*)s1, (void*)s2);
    return 1;
}

int ProcBlock_Installed(void) { return g_installed; }
int ProcBlock_BlockedCount(void) { return g_blocked; }
void ProcBlock_SetEnabled(int on) { g_enabled = on ? 1 : 0; }
int ProcBlock_Enabled(void) { return g_enabled; }
