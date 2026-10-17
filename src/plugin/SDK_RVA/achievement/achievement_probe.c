#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include "achievement_probe.h"
#include "achievement_compat.h"
#include "../console/console_cmd.h"
#include "../hook/inline_hook.h"
#include "../hook/inline_hook_batch.h"
#include "MinHook.h"
#include "../../adapter/native_adapter.h"
#define ACH_RVA(symbol) NativeAdapter_Symbol(symbol)
#include "achievement_source.h"

#include "../common/plugin_log.h"
static __declspec(thread) int g_sourceContext;
static volatile LONG g_sourceInstalled, g_sourceMounted, g_sourceLoads, g_sourceRedirects, g_sourceFailed;
static __int64 (__fastcall *g_loadDefinitions)(__int64, __int64);
static unsigned char (__fastcall *g_exists)(const char*);
static void* (__fastcall *g_lexer)(void*, const CmdString*, unsigned int);
static int (__cdecl *g_mountMemory)(const void*, unsigned __int64, void (__cdecl *)(void*), const char*, const char*, int);
static const char* (__cdecl *g_realDir)(const char*);
static unsigned char* g_sourceArchive;
static SRWLOCK g_sourceLock = SRWLOCK_INIT;

static void __cdecl SourceArchiveFree(void* data) {
    InterlockedCompareExchangePointer((PVOID volatile*)&g_sourceArchive, NULL, data);
    InterlockedExchange(&g_sourceMounted, 0);
    HeapFree(GetProcessHeap(), 0, data);
}

static int SourceHostSupported(unsigned char* base) {
    IMAGE_DOS_HEADER* dos = (IMAGE_DOS_HEADER*)base;
    IMAGE_NT_HEADERS64* nt;
    if (!base || dos->e_magic != IMAGE_DOS_SIGNATURE || dos->e_lfanew <= 0 || dos->e_lfanew > 4096) return 0;
    nt = (IMAGE_NT_HEADERS64*)(base + dos->e_lfanew);
    return nt->Signature == IMAGE_NT_SIGNATURE && NativeAdapter_GroupReady(NG_ACHIEVEMENT);
}

static int SourceMount(void) {
    wchar_t path[32768];
    DWORD count, got;
    HANDLE file = INVALID_HANDLE_VALUE;
    LARGE_INTEGER size;
    unsigned char* bytes = NULL;
    size_t total;
    int ok = 0;
    const char* real;
    AcquireSRWLockExclusive(&g_sourceLock);
    real = g_realDir(ACH_SOURCE_PATH);
    if (g_sourceMounted && real && strcmp(real, ACH_SOURCE_ARCHIVE) == 0) { ok = 1; goto done; }
    if (real) goto done;
    count = GetModuleFileNameW(NULL, path, 32768);
    if (!count || count >= 32768) goto done;
    while (count && path[count - 1] != L'\\' && path[count - 1] != L'/') --count;
    if (!count || count + 24 >= 32768) goto done;
    wcscpy_s(path + count, 32768 - count, L"common\\achievements.txt");
    file = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (file == INVALID_HANDLE_VALUE || !GetFileSizeEx(file, &size) || size.QuadPart <= 0 || size.QuadPart > ACH_SOURCE_MAX_BYTES) goto done;
    total = AchievementSource_ZipSize((size_t)size.QuadPart);
    bytes = (unsigned char*)HeapAlloc(GetProcessHeap(), 0, (SIZE_T)size.QuadPart);
    g_sourceArchive = (unsigned char*)HeapAlloc(GetProcessHeap(), 0, total);
    if (!bytes || !g_sourceArchive || !ReadFile(file, bytes, (DWORD)size.QuadPart, &got, NULL) || got != size.QuadPart) goto done;
    if (!AchievementSource_Pack(bytes, got, g_sourceArchive, total)) goto done;
    if (!g_mountMemory(g_sourceArchive, total, SourceArchiveFree, ACH_SOURCE_ARCHIVE, ACH_SOURCE_MOUNT, 0)) goto done;
    g_sourceMounted = 1;
    real = g_realDir(ACH_SOURCE_PATH);
    ok = real && strcmp(real, ACH_SOURCE_ARCHIVE) == 0;
done:
    if (file != INVALID_HANDLE_VALUE) CloseHandle(file);
    if (bytes) HeapFree(GetProcessHeap(), 0, bytes);
    if (!g_sourceMounted && g_sourceArchive) { HeapFree(GetProcessHeap(), 0, g_sourceArchive); g_sourceArchive = NULL; }
    ReleaseSRWLockExclusive(&g_sourceLock);
    return ok;
}

static unsigned char __fastcall SourceExists(const char* path) {
    if (path && AchievementSource_ShouldRedirect(g_sourceContext, path, strlen(path))) return g_exists(ACH_SOURCE_PATH);
    return g_exists(path);
}

static void* __fastcall SourceLexer(void* lexer, const CmdString* path, unsigned int mode) {
    CmdString redirected;
    const char* name = path && path->cap > 15 ? path->u.ptr : path ? path->u.buf : NULL;
    if (path && AchievementSource_ShouldRedirect(g_sourceContext, name, path->size)) {
        memset(&redirected, 0, sizeof(redirected));
        redirected.u.ptr = ACH_SOURCE_PATH; redirected.size = sizeof(ACH_SOURCE_PATH) - 1; redirected.cap = redirected.size;
        InterlockedIncrement(&g_sourceRedirects);
        return g_lexer(lexer, &redirected, mode);
    }
    return g_lexer(lexer, path, mode);
}

static __int64 __fastcall SourceLoad(__int64 manager, __int64 arg) {
    __int64 result;
    if (!SourceMount()) {
        InterlockedIncrement(&g_sourceFailed);
        Plugin_Log("[error] original achievement source unavailable; definition load skipped, no mod fallback");
        return 0;
    }
    ++g_sourceContext;
    __try { result = g_loadDefinitions(manager, arg); }
    __finally { --g_sourceContext; }
    InterlockedIncrement(&g_sourceLoads);
    AchievementCompat_DefinitionsLoaded();
    return result;
}

int AchievementSource_Install(void) {
    unsigned char* base = (unsigned char*)GetModuleHandleW(NULL);
    void* targets[3];
    int created = 0;
    if (g_sourceInstalled) return 1;
    if (!SourceHostSupported(base)) return 0;
    g_mountMemory = (void*)GetProcAddress((HMODULE)base, "?PHYSFS_mountMemory@@YAHPEBX_KP6AXPEAX@ZPEBD4H@Z");
    g_realDir = (void*)GetProcAddress((HMODULE)base, "?PHYSFS_getRealDir@@YAPEBDPEBD@Z");
    if (!g_mountMemory || !g_realDir) return 0;
    if (!InlineHook_Init()) return 0;
    targets[0] = base + ACH_RVA(NSY_ACH_SOURCE_EXISTS); targets[1] = base + ACH_RVA(NSY_ACH_SOURCE_LEXER); targets[2] = base + ACH_RVA(NSY_ACH_SOURCE_LOAD);
    if (MH_CreateHook(targets[0], SourceExists, (void**)&g_exists) != MH_OK) goto fail;
    ++created;
    if (MH_CreateHook(targets[1], SourceLexer, (void**)&g_lexer) != MH_OK) goto fail;
    ++created;
    if (MH_CreateHook(targets[2], SourceLoad, (void**)&g_loadDefinitions) != MH_OK) goto fail;
    ++created;
    if (!InlineHook_EnableQueuedBatch(targets, 3)) goto fail;
    g_sourceInstalled = 1;
    return 1;
fail:
    InlineHook_CleanupCreatedBatch(targets, created);
    return 0;
}

static long long __fastcall AchievementSourceStatus(CmdResult* out, CmdArgs* args) {
    unsigned char* base = (unsigned char*)GetModuleHandleW(NULL);
    const unsigned char* manager = NULL;
    int definitions = -1;
    char text[768];
    (void)args;
    ConsoleCmd_InitResult(out);
    if (SourceHostSupported(base)) {
        manager = *(const unsigned char**)(base + ACH_RVA(NSY_ACH_MANAGER));
        if (ConsoleCmd_IsReadable(manager, 168)) definitions = *(const int*)(manager + 28);
    }
    _snprintf_s(text, sizeof(text), _TRUNCATE,
        "[info] Original achievement source: installed=%ld mounted=%ld loads=%ld redirects=%ld failures=%ld definitions=%d. "
        "Public mod overrides ignored only inside vanilla definition loader. eligibility_compatibility_installed=%d; this status command makes no Steam calls.",
        g_sourceInstalled, g_sourceMounted, g_sourceLoads, g_sourceRedirects, g_sourceFailed, definitions, AchievementCompat_Installed());
    ConsoleCmd_SetMessage(out, text);
    out->ok = g_sourceInstalled && g_sourceMounted && g_sourceLoads > 0 && g_sourceRedirects > 0 && !g_sourceFailed;
    return (long long)out;
}

static long long __fastcall AchievementStatus(CmdResult* out, CmdArgs* args) {
    unsigned char* base = (unsigned char*)GetModuleHandleW(NULL);
    IMAGE_DOS_HEADER* dos = (IMAGE_DOS_HEADER*)base;
    IMAGE_NT_HEADERS64* nt;
    const unsigned char* manager;
    const unsigned char* state;
    char text[768];
    (void)args;
    ConsoleCmd_InitResult(out);
    if (!base || dos->e_magic != IMAGE_DOS_SIGNATURE || dos->e_lfanew <= 0 || dos->e_lfanew > 4096) {
        ConsoleCmd_SetMessage(out, "[error] Achievement probe: invalid host image."); return (long long)out;
    }
    nt = (IMAGE_NT_HEADERS64*)(base + dos->e_lfanew);
    if (nt->Signature != IMAGE_NT_SIGNATURE || !NativeAdapter_GroupReady(NG_ACHIEVEMENT)) {
        ConsoleCmd_SetMessage(out, "[error] Achievement probe: unsupported game version; no state read."); return (long long)out;
    }
    manager = *(const unsigned char**)(base + ACH_RVA(NSY_ACH_MANAGER));
    state = *(const unsigned char**)(base + ACH_RVA(NSY_GAMESTATE));
    if (!ConsoleCmd_IsReadable(manager, 168) || !ConsoleCmd_IsReadable(state, 193)) {
        ConsoleCmd_SetMessage(out, "[warning] Achievement probe: game context not ready; no state changed."); return (long long)out;
    }
    _snprintf_s(text, sizeof(text), _TRUNCATE,
        "[info] Achievement readonly status; compatibility_installed=%d. "
        "ironman=%u definitions=%d pending=%d completed=%d excluded=%d "
        "manager_flags_A0_A4=%u,%u,%u,%u,%u "
        "debug_flag=%u debug_or_crash_log_flag=%u. "
        "No SetAchievement/StoreStats/ClearAchievement/ResetAllStats calls. "
        "original_source_hook=%ld mounted=%ld loads=%ld redirects=%ld failures=%ld.",
        AchievementCompat_Installed(), state[192] & 1, *(const int*)(manager + 28), *(const int*)(manager + 52),
        *(const int*)(manager + 76), *(const int*)(manager + 100),
        manager[160], manager[161], manager[162], manager[163], manager[164],
        base[ACH_RVA(NSY_ACH_FLAG_DEBUG)], base[ACH_RVA(NSY_ACH_FLAG_LOG)],
        g_sourceInstalled, g_sourceMounted, g_sourceLoads, g_sourceRedirects, g_sourceFailed);
    ConsoleCmd_SetMessage(out, text); out->ok = 1;
    return (long long)out;
}

int AchievementProbe_RegisterCommands(void) {
    CmdDef def = {"achievementstatus", "Read achievement state without unlocking or changing eligibility", "achstatus", 0, {0}, AchievementStatus};
    CmdDef source = {"achievementsource", "Read original achievement definition source state", "achsource", 0, {0}, AchievementSourceStatus};
    int count = ConsoleCmd_RegisterAll(&def, 1);
    count += ConsoleCmd_RegisterAll(&source, 1);
    return count;
}
