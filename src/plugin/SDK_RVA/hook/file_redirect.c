#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shlobj.h>
#include <string.h>
#include <stdio.h>

#include "carrier.h"
#include "console_cmd.h"
#include "file_redirect.h"

extern void Plugin_Log(const char* fmt, ...);

typedef HANDLE (WINAPI *CreateFileWFn)(LPCWSTR, DWORD, DWORD, LPSECURITY_ATTRIBUTES,
                                       DWORD, DWORD, HANDLE);
typedef HANDLE (WINAPI *CreateFileAFn)(LPCSTR, DWORD, DWORD, LPSECURITY_ATTRIBUTES,
                                       DWORD, DWORD, HANDLE);
typedef BOOL   (WINAPI *CreateDirectoryWFn)(LPCWSTR, LPSECURITY_ATTRIBUTES);
typedef BOOL   (WINAPI *CreateDirectoryAFn)(LPCSTR, LPSECURITY_ATTRIBUTES);

static CreateFileWFn      g_origCreateFileW = NULL;
static CreateFileAFn      g_origCreateFileA = NULL;
static CreateDirectoryWFn g_origCreateDirW  = NULL;
static CreateDirectoryAFn g_origCreateDirA  = NULL;
static int                g_installed = 0;
static int                g_enabled = 1;
static char               g_gameRoot[CRASHPATH_MAX];
static char               g_sourcePrefix[CRASHPATH_MAX];
static int                g_hitCount = 0;

static unsigned char* Img(void)
{
    return (unsigned char*)GetModuleHandleA(NULL);
}

static void NormalizeSlashes(char* s)
{
    while (*s != 0) {
        if (*s == '/') *s = '\\';
        ++s;
    }
}

static void TrimSlash(char* s)
{
    size_t n = strlen(s);
    while (n > 0 && (s[n - 1] == '\\' || s[n - 1] == '/')) { s[n - 1] = 0; --n; }
}

static void WideToAnsi(const WCHAR* w, char* out, int cap)
{
    int n = WideCharToMultiByte(CP_ACP, 0, w, -1, out, cap - 1, NULL, NULL);
    if (n <= 0) { out[0] = 0; return; }
    out[cap - 1] = 0;
}

static void AnsiToWide(const char* a, WCHAR* out, int cap)
{
    int n = MultiByteToWideChar(CP_ACP, 0, a, -1, out, cap - 1);
    if (n <= 0) { out[0] = 0; return; }
    out[cap - 1] = 0;
}

static int StartsWithNoCase(const char* s, const char* prefix)
{
    size_t i = 0;
    while (prefix[i] != 0) {
        char a = s[i];
        char b = prefix[i];
        if (a >= 'A' && a <= 'Z') a = (char)(a - 'A' + 'a');
        if (b >= 'A' && b <= 'Z') b = (char)(b - 'A' + 'a');
        if (a != b) return 0;
        ++i;
    }
    return 1;
}

static void BuildSourcePrefix(void)
{
    char docs[CRASHPATH_MAX];
    WCHAR wbuf[CRASHPATH_MAX];
    docs[0] = 0;
    if (SUCCEEDED(SHGetFolderPathW(NULL, 0x0005, NULL, 0, wbuf))) {
        WideToAnsi(wbuf, docs, CRASHPATH_MAX);
    }
    if (docs[0] == 0) {
        DWORD n = GetEnvironmentVariableA("USERPROFILE", docs, CRASHPATH_MAX);
        if (n == 0 || n >= CRASHPATH_MAX) docs[0] = 0;
        if (docs[0] != 0) strncat_s(docs, CRASHPATH_MAX, "\\Documents", _TRUNCATE);
    }
    if (docs[0] == 0) return;
    strncat_s(docs, CRASHPATH_MAX, "\\Paradox Interactive\\Hearts of Iron IV\\crashes", _TRUNCATE);
    NormalizeSlashes(docs);
    TrimSlash(docs);
    strncpy_s(g_sourcePrefix, CRASHPATH_MAX, docs, _TRUNCATE);
}

static int RedirectA(const char* name, char* out, int cap, int* didRedirect)
{
    char ansi[CRASHPATH_MAX];
    const char* rest;

    if (didRedirect != NULL) *didRedirect = 0;
    if (name == NULL) return 0;
    if (g_enabled == 0) return 0;
    if (g_sourcePrefix[0] == 0 || g_gameRoot[0] == 0) return 0;

    strncpy_s(ansi, CRASHPATH_MAX, name, _TRUNCATE);
    NormalizeSlashes(ansi);
    if (!StartsWithNoCase(ansi, g_sourcePrefix)) return 0;

    rest = ansi + strlen(g_sourcePrefix);
    if (*rest != '\\') return 0;
    ++rest;
    if (*rest == 0) return 0;

    out[0] = 0;
    strncat_s(out, cap, g_gameRoot, _TRUNCATE);
    strncat_s(out, cap, "\\crashes\\", _TRUNCATE);
    strncat_s(out, cap, rest, _TRUNCATE);
    if (didRedirect != NULL) *didRedirect = 1;
    return 1;
}

static int Redirect(const WCHAR* name, WCHAR* out, int cap, int* didRedirect)
{
    char ansi[CRASHPATH_MAX];
    char built[CRASHPATH_MAX * 2];
    int did = 0;
    WideToAnsi(name, ansi, CRASHPATH_MAX);
    if (ansi[0] == 0) return 0;
    if (!RedirectA(ansi, built, CRASHPATH_MAX * 2, &did)) return 0;
    AnsiToWide(built, out, cap);
    if (out[0] == 0) return 0;
    if (didRedirect != NULL) *didRedirect = did;
    return did;
}

static HANDLE WINAPI Hook_CreateFileW(LPCWSTR name, DWORD access, DWORD share,
                                      LPSECURITY_ATTRIBUTES sa, DWORD disp,
                                      DWORD flags, HANDLE tmpl)
{
    WCHAR mapped[CRASHPATH_MAX];
    int did = 0;
    if (name != NULL && Redirect(name, mapped, CRASHPATH_MAX, &did) && did) {
        ++g_hitCount;
        Plugin_Log("[redir] CreateFileW #%d -> %ls", g_hitCount, mapped);
        return g_origCreateFileW(mapped, access, share, sa, disp, flags, tmpl);
    }
    return g_origCreateFileW(name, access, share, sa, disp, flags, tmpl);
}

static HANDLE WINAPI Hook_CreateFileA(LPCSTR name, DWORD access, DWORD share,
                                      LPSECURITY_ATTRIBUTES sa, DWORD disp,
                                      DWORD flags, HANDLE tmpl)
{
    char built[CRASHPATH_MAX * 2];
    int did = 0;
    if (RedirectA(name, built, CRASHPATH_MAX * 2, &did) && did) {
        ++g_hitCount;
        Plugin_Log("[redir] CreateFileA #%d -> %s", g_hitCount, built);
        return g_origCreateFileA(built, access, share, sa, disp, flags, tmpl);
    }
    return g_origCreateFileA(name, access, share, sa, disp, flags, tmpl);
}

static BOOL WINAPI Hook_CreateDirectoryW(LPCWSTR name, LPSECURITY_ATTRIBUTES sa)
{
    WCHAR mapped[CRASHPATH_MAX];
    int did = 0;
    if (name != NULL && Redirect(name, mapped, CRASHPATH_MAX, &did) && did) {
        ++g_hitCount;
        Plugin_Log("[redir] CreateDirectoryW #%d -> %ls", g_hitCount, mapped);
        return g_origCreateDirW(mapped, sa);
    }
    return g_origCreateDirW(name, sa);
}

static BOOL WINAPI Hook_CreateDirectoryA(LPCSTR name, LPSECURITY_ATTRIBUTES sa)
{
    char built[CRASHPATH_MAX * 2];
    int did = 0;
    if (RedirectA(name, built, CRASHPATH_MAX * 2, &did) && did) {
        ++g_hitCount;
        Plugin_Log("[redir] CreateDirectoryA #%d -> %s", g_hitCount, built);
        return g_origCreateDirA(built, sa);
    }
    return g_origCreateDirA(name, sa);
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
        if (StartsWithNoCase(dll, moduleName)) {
            IMAGE_THUNK_DATA* oft = (IMAGE_THUNK_DATA*)(img + imp->OriginalFirstThunk);
            IMAGE_THUNK_DATA* ft  = (IMAGE_THUNK_DATA*)(img + imp->FirstThunk);
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

int FileRedirect_Install(void)
{
    void** s1;
    void** s2;
    void** s3;
    void** s4;
    if (g_installed) return 1;

    GetModuleFileNameA(NULL, g_gameRoot, CRASHPATH_MAX);
    {
        char* p = g_gameRoot + strlen(g_gameRoot);
        while (p > g_gameRoot && *p != '\\' && *p != '/') --p;
        *p = 0;
    }
    NormalizeSlashes(g_gameRoot);
    TrimSlash(g_gameRoot);

    BuildSourcePrefix();
    Plugin_Log("[redir] gameRoot=[%s]", g_gameRoot);
    Plugin_Log("[redir] sourcePrefix=[%s]", g_sourcePrefix);
    if (g_sourcePrefix[0] == 0) {
        Plugin_Log("[redir] cannot build source prefix, abort");
        return 0;
    }

    s1 = FindIatSlot("kernel32.dll", "CreateFileW");
    s2 = FindIatSlot("kernel32.dll", "CreateFileA");
    s3 = FindIatSlot("kernel32.dll", "CreateDirectoryW");
    s4 = FindIatSlot("kernel32.dll", "CreateDirectoryA");
    if (s1 == NULL || s3 == NULL) {
        Plugin_Log("[redir] needed IAT slots missing (w=%p dw=%p)", (void*)s1, (void*)s3);
        return 0;
    }

    g_origCreateFileW = (CreateFileWFn)(*s1);
    g_origCreateDirW  = (CreateDirectoryWFn)(*s3);
    if (s2 != NULL) g_origCreateFileA = (CreateFileAFn)(*s2);
    if (s4 != NULL) g_origCreateDirA  = (CreateDirectoryAFn)(*s4);

    PatchSlot(s1, (void*)Hook_CreateFileW);
    PatchSlot(s3, (void*)Hook_CreateDirectoryW);
    if (s2 != NULL) PatchSlot(s2, (void*)Hook_CreateFileA);
    if (s4 != NULL) PatchSlot(s4, (void*)Hook_CreateDirectoryA);

    g_installed = 1;
    Plugin_Log("[redir] installed  W=%p A=%p DW=%p DA=%p",
               (void*)s1, (void*)s2, (void*)s3, (void*)s4);
    return 1;
}

int FileRedirect_Installed(void) { return g_installed; }
const char* FileRedirect_GameRoot(void) { return g_gameRoot; }
const char* FileRedirect_SourcePrefix(void) { return g_sourcePrefix; }
void FileRedirect_SetEnabled(int on) { g_enabled = on ? 1 : 0; }
int FileRedirect_Enabled(void) { return g_enabled; }
