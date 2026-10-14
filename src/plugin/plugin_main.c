#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>

#include "carrier.h"
#include "SDK_RVA/common/log.h"
#include "SDK_RVA/common/plugin_log.h"
#include "console_cmd.h"
#include "debug_console.h"
#include "camera_height.h"
#include "effect_reg.h"
#include "trigger_reg.h"
#include "SDK_RVA/achievement/achievement_compat.h"
#include "SDK_RVA/achievement/achievement_probe.h"
#include "SDK_RVA/achievement/achievement_ui.h"
#include "SDK_RVA/effect/effect_camera.h"
#include "SDK_RVA/effect/effect_gamedate.h"
#include "SDK_RVA/trigger/trigger_demo.h"
#include "SDK_RVA/variable64/variable64.h"
#include "SDK_RVA/variable64/array64_api.h"
#include "plugin_registration.h"
#include "adapter/native_adapter.h"

#include "file_redirect.h"
#include "process_block.h"
#include "gamedate.h"
#include "crash_test.h"


#define RVA_GS_GLOBAL   0x332F260u
#define RVA_VT_MAIN     0x2721158u
#define RVA_VT_SEC      0x27211B0u

static HMODULE g_self = NULL;

void Plugin_Log(const char* fmt, ...) {
    va_list arguments;
    va_start(arguments, fmt);
    Log_AppendV(LOADER_LOG_DIR "/mod_loader_" CARRIER_LIBRARY ".log", fmt, arguments);
    va_end(arguments);
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

static int RegisterLanguageStep(void)
{
    Var64_InstallLanguageBridge();
    return Var64_LanguageBridgeReady();
}

static PluginRegistrationStep g_effectSteps[] = {
    {"camera", EffectCameras_Register, EFF_CAMERA_COUNT, NULL, 0, 0},
    {"date", EffectGameDate_Register, EFF_DATE_COUNT, NULL, 0, 0},
    {"variable64", Var64_RegisterEffects, VAR64_EFFECT_COUNT, Var64_SyntaxHooksReady, 0, 0},
    {"array64", Array64_RegisterEffects, ARRAY64_EFFECT_COUNT, NULL, 0, 0},
    {"loadgame", Var64_RegisterLoadGameCommand, 1, NULL, 0, 0},
    {"language", RegisterLanguageStep, 1, NULL, 0, 0}
};

static PluginRegistrationStep g_triggerSteps[] = {
    {"demo", TriggerDemo_Register, TRIGGER_DEMO_COUNT, NULL, 0, 0},
    {"array64", Array64_RegisterTriggers, ARRAY64_TRIGGER_COUNT, NULL, 0, 0}
};

static void RegisterPluginGroups(const char* kind, int (*ready)(void), PluginRegistrationStep* steps, int count)
{
    int round, i, complete = 0;
    for (round = 0; round < 3000 && !complete; ++round) {
        if (ready()) complete = PluginRegistration_Poll(steps, count);
        if (!complete) Sleep(10);
    }
    for (i = 0; i < count; ++i) {
        char capability[128];
        Plugin_Log("[plugin] %s group=%s result=%d/%d complete=%d poll=%d",
            kind, steps[i].name, steps[i].last, steps[i].expected, steps[i].complete, round);
        _snprintf_s(capability, sizeof(capability), _TRUNCATE, "registration.%s.%s", kind, steps[i].name);
        NativeAdapter_Report(capability, steps[i].complete && steps[i].expected > 0,
            steps[i].expected == 0 ? "CAMERA_WRITE_CONTRACT_NOT_APPROVED" : steps[i].complete ? "EXACT_COUNT_AND_DEPENDENCIES_READY" : "REGISTRATION_INCOMPLETE");
    }
    if (!complete) Plugin_Log("[plugin] %s registration incomplete after %d polls", kind, round);
}

static DWORD WINAPI PluginThread(LPVOID p)
{
    int i;
    int source, compat, ui;
    static const char* capabilities[] = {
        "achievement.source", "achievement.compatibility", "achievement.ui", "redirect.files", "redirect.process", "console.commands",
        "registration.effects.camera", "registration.effects.date", "registration.effects.variable64", "registration.effects.array64", "registration.effects.loadgame", "registration.effects.language",
        "registration.triggers.demo", "registration.triggers.array64", "commands.camera", "commands.camera.read", "commands.clock", "commands.crash", "commands.achievement", "ui.date"
    };
    (void)p;
    Plugin_Log("[plugin] thread start, pid=%lu", (unsigned long)GetCurrentProcessId());
    Plugin_Log("[plugin] hoi4 base=%p", (void*)GetModuleHandleA(NULL));
    NativeAdapter_Initialize();
    Plugin_Log("[adapter] legacy=%d reason=%s", NativeAdapter_LegacyAllowed(), NativeAdapter_Diagnostic());
    for (i = 0; i < (int)(sizeof(capabilities) / sizeof(capabilities[0])); ++i)
        NativeAdapter_Report(capabilities[i], 0, NativeAdapter_LegacyAllowed() ? "INITIALIZING" : "LEGACY_BUILD_UNREVIEWED");
    NativeAdapter_StartMonitor();
    if (!NativeAdapter_LegacyAllowed()) {
        NativeAdapter_OpenLogConsole();
        Plugin_Log("[adapter] legacy initialization blocked before any business hook or registry access");
        return 0;
    }
    source = AchievementSource_Install(); compat = AchievementCompat_Install(); ui = AchievementUi_Install();
    Plugin_Log("[plugin] AchievementSource_Install -> %d", source);
    Plugin_Log("[plugin] AchievementCompat_Install -> %d", compat);
    Plugin_Log("[plugin] AchievementUi_Install -> %d", ui);
    NativeAdapter_Report("achievement.source", source, source ? "INSTALLED" : "INSTALL_FAILED");
    NativeAdapter_Report("achievement.compatibility", compat, compat ? "INSTALLED" : "INSTALL_FAILED");
    NativeAdapter_Report("achievement.ui", ui, ui ? "INSTALLED" : "INSTALL_FAILED");

    {
        int ok = FileRedirect_Install();
        NativeAdapter_Report("redirect.files", ok, ok ? "INSTALLED" : "INSTALL_FAILED");
        Plugin_Log("[plugin] FileRedirect_Install -> %d (gameRoot=%s)",
                   ok, FileRedirect_GameRoot());
    }

    {
        int ok = ProcBlock_Install();
        if (!ProcBlock_Complete()) ProcBlock_SetEnabled(0);
        NativeAdapter_Report("redirect.process", ProcBlock_Complete(), ProcBlock_Complete() ? "A_AND_W_INSTALLED" : ok ? "PARTIAL_INSTALL" : "INSTALL_FAILED");
        Plugin_Log("[plugin] ProcBlock_Install -> %d", ok);
    }

    DebugConsole_Start();

    if (!NativeAdapter_CameraWriteAllowed()) {
        g_effectSteps[0].run = NULL;
        g_effectSteps[0].expected = 0;
        g_effectSteps[0].complete = 1;
    }

    if (NativeAdapter_RegistryReady()) {
    RegisterPluginGroups("effects", Effect_RegistryReady, g_effectSteps,
        (int)(sizeof(g_effectSteps) / sizeof(g_effectSteps[0])));
    RegisterPluginGroups("triggers", Trigger_RegistryReady, g_triggerSteps,
        (int)(sizeof(g_triggerSteps) / sizeof(g_triggerSteps[0])));
    } else {
        for (i = 0; i < 6; ++i) {
            char capability[128];
            _snprintf_s(capability, sizeof(capability), _TRUNCATE, "registration.effects.%s", g_effectSteps[i].name);
            NativeAdapter_Report(capability, 0, NativeAdapter_RegistryDiagnostic());
        }
        for (i = 0; i < 2; ++i) {
            char capability[128];
            _snprintf_s(capability, sizeof(capability), _TRUNCATE, "registration.triggers.%s", g_triggerSteps[i].name);
            NativeAdapter_Report(capability, 0, NativeAdapter_RegistryDiagnostic());
        }
    }
    NativeAdapter_CameraRegistered(0, g_effectSteps[0].expected > 0 && g_effectSteps[0].complete ? g_effectSteps[0].last : 0);

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
        int n = NativeAdapter_CameraWriteAllowed() ? Camera_RegisterCommands() : 0;
        Plugin_Log("[plugin] Camera_RegisterCommands -> %d", n);
        NativeAdapter_CameraRegistered(n, g_effectSteps[0].expected > 0 && g_effectSteps[0].complete ? g_effectSteps[0].last : 0);
        NativeAdapter_Report("commands.camera", n == 3, n == 3 ? "THREE_COMMANDS_REGISTERED" : "WRITE_CONTRACT_OR_REGISTRATION_FAILED");
        {
            int readCommand = Camera_RegisterReadCommand();
            Plugin_Log("[plugin] Camera_RegisterReadCommand -> %d", readCommand);
            NativeAdapter_Report("commands.camera.read", readCommand == 1, readCommand == 1 ? "REGISTERED" : "REGISTRATION_FAILED");
        }
    }

    {
        int n = GameDate_RegisterCommands();
        Plugin_Log("[plugin] GameDate_RegisterCommands -> %d", n);
        NativeAdapter_Report("commands.clock", n == 5, n == 5 ? "FIVE_COMMANDS_REGISTERED" : "REGISTRATION_INCOMPLETE");
    }

    {
        int r = GameDateUi_Init();
        Plugin_Log("[plugin] GameDateUi_Init -> %d", r);
        NativeAdapter_Report("ui.date", r > 0, r > 0 ? "READY" : "INIT_FAILED");
    }

    {
        int n = CrashTest_RegisterCommands();
        Plugin_Log("[plugin] CrashTest_RegisterCommands -> %d", n);
        NativeAdapter_Report("commands.crash", n == 2, n == 2 ? "TWO_COMMANDS_REGISTERED" : "REGISTRATION_INCOMPLETE");
    }

    source = AchievementProbe_RegisterCommands(); compat = AchievementCompat_RegisterCommands(); ui = AchievementUi_RegisterCommands();
    Plugin_Log("[plugin] AchievementProbe_RegisterCommands -> %d", source);
    Plugin_Log("[plugin] AchievementCompat_RegisterCommands -> %d", compat);
    Plugin_Log("[plugin] AchievementUi_RegisterCommands -> %d", ui);
    NativeAdapter_Report("commands.achievement", source == 2 && compat == 1 && ui == 1, source == 2 && compat == 1 && ui == 1 ? "ALL_FOUR_COMMANDS_REGISTERED" : "REGISTRATION_INCOMPLETE");
    DebugConsole_RegisterCommands();
    Plugin_Log("[plugin] NativeAdapter_RegisterScriptDiagnostic -> %d", NativeAdapter_RegisterScriptDiagnostic());

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
