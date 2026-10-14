#include <windows.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <vector>

#include "carrier.h"
#include "../plugin/SDK_RVA/common/log.h"

static void LogPath(char* out, size_t n) {
    _snprintf_s(out, n, _TRUNCATE, "%s/mod_loader_" CARRIER_LIBRARY ".log", LOADER_LOG_DIR);
}

static void PLog(const char* fmt, ...) {
    char path[MAX_PATH];
    va_list arguments;
    LogPath(path, sizeof(path));
    va_start(arguments, fmt);
    Log_AppendV(path, fmt, arguments);
    va_end(arguments);
}

static BYTE* g_image = NULL;
static unsigned long g_crt_rva = 0;

struct FuncRange { unsigned long begin, end; };

static const IMAGE_SECTION_HEADER* FindSection(BYTE* image, unsigned long rva,
                                               unsigned long size, bool* writable) {
    const IMAGE_DOS_HEADER* dos = (const IMAGE_DOS_HEADER*)image;
    const IMAGE_NT_HEADERS* nt = (const IMAGE_NT_HEADERS*)(image + dos->e_lfanew);
    const IMAGE_SECTION_HEADER* sec = IMAGE_FIRST_SECTION(nt);
    unsigned i;
    for (i = 0; i < nt->FileHeader.NumberOfSections; ++i, ++sec) {
        unsigned long vsize = sec->Misc.VirtualSize ? sec->Misc.VirtualSize : sec->SizeOfRawData;
        if (rva >= sec->VirtualAddress && rva + size <= sec->VirtualAddress + vsize) {
            if (writable) *writable = (sec->Characteristics & IMAGE_SCN_MEM_WRITE) != 0;
            return sec;
        }
    }
    return NULL;
}

static void ReadFunctions(BYTE* image, std::vector<FuncRange>& out) {
    const IMAGE_DOS_HEADER* dos = (const IMAGE_DOS_HEADER*)image;
    const IMAGE_NT_HEADERS* nt = (const IMAGE_NT_HEADERS*)(image + dos->e_lfanew);
    const IMAGE_SECTION_HEADER* sec = IMAGE_FIRST_SECTION(nt);
    unsigned i, j;
    for (i = 0; i < nt->FileHeader.NumberOfSections; ++i, ++sec) {
        if (memcmp(sec->Name, ".pdata", 6) != 0) continue;
        {
            unsigned count = sec->Misc.VirtualSize / sizeof(RUNTIME_FUNCTION);
            const RUNTIME_FUNCTION* rf = (const RUNTIME_FUNCTION*)(image + sec->VirtualAddress);
            for (j = 0; j < count; ++j) {
                if (rf[j].BeginAddress != 0) {
                    FuncRange f;
                    f.begin = rf[j].BeginAddress;
                    f.end = rf[j].EndAddress;
                    out.push_back(f);
                }
            }
        }
    }
}

static unsigned long FunctionStart(const std::vector<FuncRange>& funcs, unsigned long rva) {
    size_t lo = 0, hi = funcs.size();
    while (lo < hi) {
        size_t mid = (lo + hi) / 2;
        if (funcs[mid].begin <= rva) lo = mid + 1; else hi = mid;
    }
    if (lo == 0) return 0;
    {
        const FuncRange& f = funcs[lo - 1];
        return (rva < f.end) ? f.begin : 0;
    }
}

static const FuncRange* FunctionOf(const std::vector<FuncRange>& funcs, unsigned long rva) {
    unsigned long begin = FunctionStart(funcs, rva);
    size_t i;
    if (begin == 0) return NULL;
    for (i = 0; i < funcs.size(); ++i) {
        if (funcs[i].begin == begin) return &funcs[i];
    }
    return NULL;
}

static bool DecodeIndexTest(const BYTE* code, unsigned long rva, unsigned long* target) {
    if (code[0] == 0x83 && code[1] == 0x3D && code[6] == 0xFF) {
        *target = rva + 7 + *(const int*)(code + 2);
        return true;
    }
    if (code[0] == 0x81 && code[1] == 0x3D &&
        *(const unsigned*)(code + 3) == 0xFFFFFFFFu) {
        *target = rva + 10 + *(const int*)(code + 2);
        return true;
    }
    return false;
}

static void CrtProbeLocate(HMODULE main_module) {
    const IMAGE_DOS_HEADER* dos;
    const IMAGE_NT_HEADERS* nt;
    const IMAGE_SECTION_HEADER* text = NULL;
    const IMAGE_SECTION_HEADER* sec;
    std::vector<FuncRange> funcs;
    unsigned long begin, end, rva;
    std::vector<unsigned long> aborts, getters, found;
    size_t i;
    static const BYTE kFastFail[] = {0xB9, 0x07, 0x00, 0x00, 0x00, 0xCD, 0x29};

    g_image = (BYTE*)main_module;
    if (g_image == NULL) return;
    dos = (const IMAGE_DOS_HEADER*)g_image;
    if (dos->e_magic != IMAGE_DOS_SIGNATURE) return;
    nt = (const IMAGE_NT_HEADERS*)(g_image + dos->e_lfanew);
    if (nt->Signature != IMAGE_NT_SIGNATURE) return;
    if (nt->FileHeader.Machine != IMAGE_FILE_MACHINE_AMD64) return;

    ReadFunctions(g_image, funcs);
    if (funcs.empty()) return;

    sec = IMAGE_FIRST_SECTION(nt);
    for (i = 0; i < nt->FileHeader.NumberOfSections; ++i, ++sec) {
        if (memcmp(sec->Name, ".text", 5) == 0) text = sec;
    }
    if (text == NULL) return;
    begin = text->VirtualAddress;
    end = begin + (text->Misc.VirtualSize ? text->Misc.VirtualSize : text->SizeOfRawData);

    for (rva = begin; rva + sizeof(kFastFail) < end; ++rva) {
        unsigned long entry;
        bool known = false;
        if (memcmp(g_image + rva, kFastFail, sizeof(kFastFail)) != 0) continue;
        entry = FunctionStart(funcs, rva);
        if (entry == 0) continue;
        for (i = 0; i < aborts.size(); ++i) if (aborts[i] == entry) known = true;
        if (!known) aborts.push_back(entry);
    }
    if (aborts.empty()) return;

    for (rva = begin; rva + 5 < end; ++rva) {
        unsigned long target, back;
        bool to_abort = false, guarded = false;
        if (g_image[rva] != 0xE8) continue;
        target = rva + 5 + *(const int*)(g_image + rva + 1);
        for (i = 0; i < aborts.size(); ++i) if (aborts[i] == target) to_abort = true;
        if (!to_abort) continue;
        for (back = 1; back <= 0x20 && rva >= back; ++back) {
            const BYTE* p = g_image + rva - back;
            if (p[0] == 0x48 && p[1] == 0x85 && p[2] == 0xC0) { guarded = true; break; }
        }
        if (!guarded) continue;
        for (back = 1; back <= 0x20 && rva >= back; ++back) {
            const BYTE* p = g_image + rva - back;
            unsigned long call, entry;
            bool to_abort2 = false, known = false;
            if (p[0] != 0xE8) continue;
            call = rva - back + 5 + *(const int*)(p + 1);
            entry = FunctionStart(funcs, call);
            if (entry == 0 || entry != call) continue;
            for (i = 0; i < aborts.size(); ++i) if (aborts[i] == entry) to_abort2 = true;
            if (to_abort2) continue;
            for (i = 0; i < getters.size(); ++i) if (getters[i] == entry) known = true;
            if (!known) getters.push_back(entry);
            break;
        }
    }
    if (getters.empty()) return;

    for (i = 0; i < getters.size(); ++i) {
        unsigned long entry = getters[i];
        const FuncRange* f = FunctionOf(funcs, entry);
        unsigned long target = 0, test_at = 0, test_len, k, r2;
        const BYTE* after;
        const BYTE* next;
        unsigned long after_len;
        bool read_back = false, writable = false, known = false;
        DWORD value;

        if (f == NULL || f->end <= f->begin + 16) continue;
        for (k = 0; k + 10 < 0x40 && entry + k + 10 < f->end; ++k) {
            if (DecodeIndexTest(g_image + entry + k, entry + k, &target)) { test_at = entry + k; break; }
        }
        if (test_at == 0) continue;
        test_len = (g_image[test_at] == 0x83) ? 7 : 10;
        after = g_image + test_at + test_len;
        if (after[0] != 0x75 && after[0] != 0x0F) continue;
        after_len = (after[0] == 0x0F) ? 6 : 2;
        next = g_image + test_at + test_len + after_len;
        if (next[0] != 0xEB && next[0] != 0xE9) {
            unsigned long set_len = 0;
            if ((next[0] == 0x31 || next[0] == 0x33) && next[1] == 0xC0) set_len = 2;
            else if (next[0] == 0xB8 && next[1] == 0 && next[2] == 0 && next[3] == 0 && next[4] == 0) set_len = 5;
            if (set_len == 0) continue;
            if (next[set_len] != 0xEB && next[set_len] != 0xE9) continue;
        }
        for (r2 = test_at + test_len; r2 + 6 < f->end; ++r2) {
            const BYTE* q = g_image + r2;
            if (q[0] == 0x8B && (q[1] & 0xC7) == 0x05) {
                if (r2 + 6 + *(const int*)(q + 2) == target) read_back = true;
            }
        }
        if (!read_back) continue;
        if (FindSection(g_image, target, sizeof(DWORD), &writable) == NULL || !writable) continue;
        value = *(const DWORD*)(g_image + target);
        if (value != 0xFFFFFFFFu && value > 0x4000u) continue;
        for (k = 0; k < found.size(); ++k) if (found[k] == target) known = true;
        if (!known) found.push_back(target);
    }

    if (found.size() != 1) return;
    g_crt_rva = found[0];
}

static bool CrtReady(void) {
    if (g_crt_rva == 0 || g_image == NULL) return false;
    return *(const DWORD*)(g_image + g_crt_rva) != 0xFFFFFFFFu;
}

enum StartHow {
    ST_ATTACH = 0, ST_THREAD_ATTACH, ST_MSGLOOP, ST_GIVEUP, ST_NOWAKEUP, ST_FALLBACK
};

static HMODULE g_self = NULL;
static DWORD g_attach_tick = 0;
static volatile LONG g_armed = 0;
static volatile LONG g_started = 0;
static unsigned long g_start_ms = 0;
static StartHow g_start_how = ST_ATTACH;

static const unsigned long kNoProbeSafeMs = 700;

static const unsigned long kDelayMs = 700;

static const unsigned long kGiveUpMs = 30000;

static unsigned long ProcessUptimeMs(void) { return GetTickCount() - g_attach_tick; }

static bool SafeToStart(void) {
    if (g_crt_rva != 0) return CrtReady();
    return ProcessUptimeMs() >= kNoProbeSafeMs;
}

static bool ClaimStart(void) { return InterlockedCompareExchange(&g_started, 1, 0) == 0; }

static DWORD WINAPI Worker(void* param);

static void StartInline(StartHow how) {
    g_start_how = how;
    g_start_ms = ProcessUptimeMs();
    Worker((void*)(uintptr_t)how);
}

static void StartThread(StartHow how) {
    HANDLE t;
    g_start_how = how;
    g_start_ms = ProcessUptimeMs();
    t = CreateThread(NULL, 0, Worker, (void*)(uintptr_t)how, 0, NULL);
    if (t != NULL) { CloseHandle(t); return; }

    StartInline(how);
}

static UINT_PTR g_timer = 0;
static UINT_PTR (WINAPI* g_set_timer)(HWND, UINT_PTR, UINT, TIMERPROC) = NULL;
static BOOL (WINAPI* g_kill_timer)(HWND, UINT_PTR) = NULL;

static void ArmDeferredStart(void);

static VOID CALLBACK OnTimer(HWND, UINT, UINT_PTR, DWORD) {
    if (g_started != 0) {
        if (g_timer != 0 && g_kill_timer) g_kill_timer(NULL, g_timer);
        return;
    }
    if (SafeToStart()) {
        if (ClaimStart()) {
            if (g_timer != 0 && g_kill_timer) g_kill_timer(NULL, g_timer);
            StartThread(ST_MSGLOOP);
        }
        return;
    }
    if (ProcessUptimeMs() >= kGiveUpMs) {
        if (ClaimStart()) StartInline(ST_GIVEUP);
    }
}

static bool ArmTimer(unsigned long after_ms) {
    HMODULE user32 = GetModuleHandleW(L"user32.dll");
    if (user32 == NULL) user32 = LoadLibraryW(L"user32.dll");
    if (user32 == NULL) return false;
    g_set_timer = (UINT_PTR (WINAPI*)(HWND, UINT_PTR, UINT, TIMERPROC))
        (void*)GetProcAddress(user32, "SetTimer");
    g_kill_timer = (BOOL (WINAPI*)(HWND, UINT_PTR))
        (void*)GetProcAddress(user32, "KillTimer");
    if (g_set_timer == NULL) return false;
    g_timer = g_set_timer(NULL, 0, (UINT)after_ms, OnTimer);
    return g_timer != 0;
}

static void ArmDeferredStart(void) {
    if (SafeToStart()) {
        if (ClaimStart()) StartThread(ST_ATTACH);
        return;
    }
    InterlockedExchange(&g_armed, 1);
    if (!ArmTimer(kNoProbeSafeMs)) {
        if (ClaimStart()) StartThread(ST_NOWAKEUP);
    }
}

static const char* kPluginNames[] = {
    "hoi4_mod_plugin.dll",
    "mod_plugin.dll",
    "plugin.dll",
    NULL
};

static bool FileExistsA(const char* p) {
    DWORD a = GetFileAttributesA(p);
    return a != INVALID_FILE_ATTRIBUTES && !(a & FILE_ATTRIBUTE_DIRECTORY);
}

static bool TryLoadPlugin(const char* dir, const char* where) {
    char dllPath[MAX_PATH];
    int i;
    for (i = 0; kPluginNames[i] != NULL; ++i) {
        HMODULE m;
        _snprintf_s(dllPath, sizeof(dllPath), _TRUNCATE, "%s\\%s", dir, kPluginNames[i]);
        if (!FileExistsA(dllPath)) continue;
        PLog("[carrier] %s found plugin %s", where, kPluginNames[i]);
        m = LoadLibraryA(dllPath);
        if (m != NULL) {
            PLog("[case2] plugin loaded: %s", dllPath);
            PLog("         base=%p   name=%s", (void*)m, kPluginNames[i]);
            return true;
        }
        PLog("[carrier] load failed: %s  err=%lu", dllPath, GetLastError());
    }
    return false;
}

static void ScanAndLoad(void) {
    char dir[MAX_PATH];
    char* p;
    int loaded = 0;

    if (GetModuleFileNameA(NULL, dir, MAX_PATH) == 0) {
        PLog("[carrier] no main module path, err=%lu", GetLastError());
        return;
    }
    p = strrchr(dir, '\\');
    if (p == NULL) {
        PLog("[carrier] bad main module path: %s", dir);
        return;
    }
    *p = '\0';

    PLog("[carrier] game root = %s", dir);
    if (TryLoadPlugin(dir, "gameroot")) ++loaded;
    PLog("[carrier] done: %d plugin(s) loaded", loaded);
}

static DWORD WINAPI Worker(void* param) {
    StartHow how = (StartHow)(uintptr_t)param;
    char exePath[MAX_PATH];
    const char* exeName;
    unsigned long uptime;
    HANDLE mutex;
    bool holding = false;

    PLog("==================================================");
    PLog("[case1] game-root " CARRIER_LIBRARY ".dll loaded by game");
    PLog("         pid=%lu  self=%p", GetCurrentProcessId(), (void*)g_self);
    GetModuleFileNameA(NULL, exePath, MAX_PATH);
    exeName = strrchr(exePath, '\\');
    exeName = exeName ? exeName + 1 : exePath;
    PLog("         main=%p (%s)", (void*)GetModuleHandleA(NULL), exeName);
    {

        char selfPath[MAX_PATH];
        GetModuleFileNameA(g_self, selfPath, MAX_PATH);
        PLog("         carrier path = %s", selfPath);
    }
    PLog("==================================================");

    if (g_crt_rva != 0) {
        PLog("crt   : per-thread data flag at %s+0x%lx, %s", exeName, g_crt_rva,
             CrtReady() ? "ready" : "never became ready");
    } else {
        PLog("crt   : no per-thread data flag found in %s; time only", exeName);
    }
    switch (how) {
    case ST_ATTACH:        PLog("start : the game's CRT was already up at attach"); break;
    case ST_THREAD_ATTACH: PLog("start : a thread attached after the CRT was up (%lu ms)", g_start_ms); break;
    case ST_MSGLOOP:       PLog("start : the message loop started (%lu ms)", g_start_ms); break;
    case ST_GIVEUP:        PLog("start : the CRT stayed unready for %lu ms; loading inline", g_start_ms); break;
    case ST_NOWAKEUP:      PLog("start : no user32 for a deferred start; thread started at attach"); break;
    default:               PLog("start : fallback"); break;
    }

    if (_stricmp(exeName, "hoi4.exe") != 0) {
        PLog("host is not hoi4.exe; nothing to do");
        return 0;
    }

    uptime = ProcessUptimeMs();
    if (uptime < kDelayMs) {
        PLog("waiting %lu ms before loading (the process is %lu ms old)", kDelayMs - uptime, uptime);
        Sleep(kDelayMs - uptime);
    }

    {
        char mutexName[64];
        _snprintf_s(mutexName, sizeof(mutexName), _TRUNCATE,
                    "Local\\hoi4_mod_loader_%lu", GetCurrentProcessId());
        mutex = CreateMutexA(NULL, FALSE, mutexName);
    }
    if (mutex != NULL) {
        holding = WaitForSingleObject(mutex, 60000) == WAIT_OBJECT_0;
        if (!holding) PLog("[carrier] another carrier holds lock");
    }

    ScanAndLoad();

    if (mutex != NULL) {
        if (holding) ReleaseMutex(mutex);
        CloseHandle(mutex);
    }
    return 0;
}

BOOL WINAPI DllMain(HINSTANCE instance, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        g_self = instance;
        g_attach_tick = GetTickCount();
#ifdef CARRIER_EARLY_THREAD

        CrtProbeLocate(GetModuleHandleW(NULL));
        {
            HANDLE t = CreateThread(NULL, 0, Worker, (void*)(uintptr_t)ST_ATTACH, 0, NULL);
            if (t != NULL) CloseHandle(t);
        }
        return TRUE;
    }
#else

        CrtProbeLocate(GetModuleHandleW(NULL));
        ArmDeferredStart();
    } else if (reason == DLL_THREAD_ATTACH) {

        if (g_armed != 0 && g_started == 0 && SafeToStart() && ClaimStart()) {
            StartThread(ST_THREAD_ATTACH);
        }
    }
#endif
    return TRUE;
}
