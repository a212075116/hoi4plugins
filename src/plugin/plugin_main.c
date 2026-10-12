#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>

#include "carrier.h"
#include "console_cmd.h"
#include "camera_height.h"
#include "effect_reg.h"
#include "trigger_reg.h"

int TriggerDemo_Register(void);
#include "file_redirect.h"
#include "process_block.h"
#include "gamedate.h"
#include "crash_test.h"

int EffectCameras_Register(void);
int EffectGameDate_Register(void);
int Var64_RegisterEffects(void);
int Var64_RegisterLoadGameCommand(void);
void Var64_InstallLanguageBridge(void);
int Array64_RegisterEffects(void);
int Array64_RegisterTriggers(void);

#define RVA_GS_GLOBAL   0x332F260u
#define RVA_VT_MAIN     0x2721158u
#define RVA_VT_SEC      0x27211B0u

static HMODULE g_self = NULL;

void Plugin_Log(const char* fmt, ...)
{
    char buf[2048];
    char path[MAX_PATH];
    SYSTEMTIME st;
    HANDLE h;
    DWORD written = 0;
    va_list ap;
    int n;

    va_start(ap, fmt);
    n = _vsnprintf_s(buf, sizeof(buf), _TRUNCATE, fmt, ap);
    va_end(ap);
    if (n < 0) return;

    GetLocalTime(&st);
    _snprintf_s(path, sizeof(path), _TRUNCATE,
                "%s/mod_loader_" CARRIER_LIBRARY ".log", LOADER_LOG_DIR);
    h = CreateFileA(path, FILE_APPEND_DATA, FILE_SHARE_READ | FILE_SHARE_WRITE,
                    NULL, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (h == INVALID_HANDLE_VALUE) return;
    {
        char line[2304];
        int m = _snprintf_s(line, sizeof(line), _TRUNCATE,
                            "[%02d:%02d:%02d.%03d] %s\r\n",
                            st.wHour, st.wMinute, st.wSecond, st.wMilliseconds, buf);
        if (m > 0) WriteFile(h, line, (DWORD)m, &written, NULL);
    }
    CloseHandle(h);
}

static void VerifyClassStructure(void)
{
    HMODULE base = GetModuleHandleA(NULL);
    unsigned char* img = (unsigned char*)base;
    void* vtWantMain;
    void* vtWantSec;
    unsigned char* obj;
    int ok = 0;

    if (base == NULL) {
        Plugin_Log("[verify] no module base");
        return;
    }
    vtWantMain = (void*)(img + RVA_VT_MAIN);
    vtWantSec = (void*)(img + RVA_VT_SEC);

    if (!ConsoleCmd_IsReadable(img + RVA_GS_GLOBAL, sizeof(void*))) {
        Plugin_Log("[verify] global slot unreadable");
        return;
    }
    obj = (unsigned char*)(*(void**)(img + RVA_GS_GLOBAL));
    if (obj == NULL) {
        Plugin_Log("[verify] CCurrentGameState* is NULL");
        return;
    }
    if (!ConsoleCmd_IsReadable(obj, 0x60)) {
        Plugin_Log("[verify] object unreadable: %p", (void*)obj);
        return;
    }

    ok += (*(void**)obj == vtWantMain);
    ok += (*(void**)(obj + 8) == vtWantSec);
    Plugin_Log("[verify] obj=%p vt0=%p vt8=%p match=%d/2",
               (void*)obj, *(void**)obj, *(void**)(obj + 8), ok);
}

static int ScanKnownArrays(void)
{
    static const struct { const char* name; unsigned long rva; } kKnown[] = {
        { "CCountry",   0x27E7360ul },
        { "CState",     0x2936CC0ul },
        { "CProvince",  0x2971B18ul },
        { "CCharacter", 0x297EA60ul },
        { "CArmy",      0x295A2B0ul },
        { "CUnit",      0x29530D8ul },
        { "CDecision",  0x27EB3D0ul },
        { "CEffect",    0x27D4990ul },
        { "CTrigger",   0x27D55F0ul },
        { NULL, 0 }
    };
    HMODULE base = GetModuleHandleA(NULL);
    unsigned char* img = (unsigned char*)base;
    unsigned char* obj;
    int off;
    int total = 0;

    if (base == NULL) return 0;
    obj = (unsigned char*)(*(void**)(img + RVA_GS_GLOBAL));
    if (obj == NULL) return 0;

    for (off = 0; off + 24 <= 0x1200; off += 8) {
        unsigned long long ptr = *(unsigned long long*)(obj + off);
        unsigned long long size = *(unsigned long long*)(obj + off + 8);
        int k;

        if (size < 2 || size > 100000) continue;
        if (ptr < 0x10000ULL) continue;
        if (ptr > 0x00007FFFFFFFFFFFULL) continue;

        for (k = 0; kKnown[k].name != NULL; ++k) {
            void* want = (void*)(img + kKnown[k].rva);
            int hits = 0;
            unsigned long long j;
            unsigned long long limit = size < 8 ? size : 8;

            if (!ConsoleCmd_IsReadable((const void*)(uintptr_t)ptr, (size_t)(limit * 8))) continue;
            for (j = 0; j < limit; ++j) {
                if (*(void**)((unsigned char*)(ptr + j * 8)) == want) ++hits;
            }
            if (hits > 0) {
                Plugin_Log("[scan] hit %s at CGameState+0x%X ptr=%p size=%llu hits=%d",
                           kKnown[k].name, off, (void*)(uintptr_t)ptr, size, hits);
                ++total;
            }
        }
    }
    return total;
}

static DWORD WINAPI PluginThread(LPVOID p)
{
    int i;
    (void)p;
    Plugin_Log("[plugin] thread start, pid=%lu", (unsigned long)GetCurrentProcessId());
    Plugin_Log("[plugin] hoi4 base=%p", (void*)GetModuleHandleA(NULL));

    {
        int ok = FileRedirect_Install();
        Plugin_Log("[plugin] FileRedirect_Install -> %d (gameRoot=%s)",
                   ok, FileRedirect_GameRoot());
    }

    {
        int ok = ProcBlock_Install();
        Plugin_Log("[plugin] ProcBlock_Install -> %d", ok);
    }

    {
        int round;
        int ok = 0;
        int readyAt = -1;
        for (round = 0; round < 3000 && !ok; ++round) {
            if (Effect_RegistryReady()) {
                if (readyAt < 0) {
                    readyAt = round;
                    Plugin_Log("[plugin] lexer ready at poll %d", round);
                }
                ok = (EffectCameras_Register() > 0);
                if (ok) {
                    Plugin_Log("[plugin] effects registered at poll %d, count=%d",
                               round, Effect_RegistryRegisteredCount());
                }
                if (ok) {
                    int nd = EffectGameDate_Register();
                    Plugin_Log("[plugin] date effects registered: %d", nd);
                }
                if (ok) {
                    int nv = Var64_RegisterEffects();
                    Plugin_Log("[plugin] var64 effects registered: %d", nv);
                    Plugin_Log("[plugin] array64 effects registered: %d", Array64_RegisterEffects());
                }
                if (ok) {
                    int nl = Var64_RegisterLoadGameCommand();
                    Plugin_Log("[plugin] loadgame command registered: %d", nl);
                }
                if (ok) {
                    Var64_InstallLanguageBridge();
                }
            }
            if (!ok) Sleep(10);
        }
        if (!ok) Plugin_Log("[plugin] gave up waiting for lexer (polls=%d)", round);
    }

    {
        int round;
        int registered = 0;
        for (round = 0; round < 3000 && registered == 0; ++round) {
            if (Trigger_RegistryReady()) registered = TriggerDemo_Register();
            if (registered == 0) Sleep(10);
        }
        Plugin_Log("[plugin] triggers registered: %d/3 (poll=%d)", registered, round);
        Plugin_Log("[plugin] array64 triggers registered: %d", Array64_RegisterTriggers());
    }

    for (i = 0; i < 300; ++i) {
        void* cur = NULL;
        HMODULE b = GetModuleHandleA(NULL);
        if (b != NULL) cur = *(void**)((unsigned char*)b + RVA_GS_GLOBAL);
        if (cur != NULL) break;
        Sleep(200);
    }
    VerifyClassStructure();

    {
        int round;
        int got = 0;
        for (round = 0; round < 600 && !got; ++round) {
            got = Camera_CaptureTrueUpperLimit();
            if (!got) Sleep(50);
        }
        if (!got) Plugin_Log("[plugin] true upper limit not captured after %d polls", round);
    }

    {
        int n = Camera_RegisterCommands();
        Plugin_Log("[plugin] Camera_RegisterCommands -> %d", n);
    }

    {
        int n = GameDate_RegisterCommands();
        Plugin_Log("[plugin] GameDate_RegisterCommands -> %d", n);
    }

    {
        int r = GameDateUi_Init();
        Plugin_Log("[plugin] GameDateUi_Init -> %d", r);
    }

    {
        int n = CrashTest_RegisterCommands();
        Plugin_Log("[plugin] CrashTest_RegisterCommands -> %d", n);
    }

    {
        int round;
        int found = 0;
        for (round = 0; round < 2400 && found == 0; ++round) {
            found = ScanKnownArrays();
            if (found == 0) Sleep(1000);
        }
        if (found == 0) Plugin_Log("[scan] no known class array found");
    }
    return 0;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID r)
{
    (void)r;
    if (reason == DLL_PROCESS_ATTACH) {
        HANDLE t;
        DisableThreadLibraryCalls(h);
        g_self = (HMODULE)h;
        t = CreateThread(NULL, 0, PluginThread, NULL, 0, NULL);
        if (t) CloseHandle(t);
    }
    return TRUE;
}
