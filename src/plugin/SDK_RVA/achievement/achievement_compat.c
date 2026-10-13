#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include "achievement_compat.h"
#include "../console/console_cmd.h"
#include "../hook/inline_hook.h"
#include "MinHook.h"

#include "../common/plugin_log.h"
typedef unsigned char (__fastcall *Unary)(void*);
typedef unsigned char (__fastcall *Eval)(void*, void*);
typedef void (__fastcall *Operation)(unsigned char*, void*);
static unsigned char* g_base;
static Unary g_eligible, g_iron;
static Operation g_rebuild, g_restore, g_update;
static __declspec(thread) int g_possible;
static volatile LONG g_installed, g_needRebuild = 1, g_rebuilds, g_ticks, g_nativeCompletions, g_ironOverrides;

static int NativeGate(const unsigned char* manager) {
    return manager[163] || (manager[161] && manager[162] && !g_base[0x34530D4] && !g_base[0x332EC69]);
}

static int Compatible(unsigned char* manager) {
    unsigned char* console;
    unsigned char** definitions;
    unsigned char* backend;
    unsigned char* context;
    void* network;
    void** table;
    if (!g_installed || !ConsoleCmd_IsReadable(manager, 168) || manager[160] || manager[163] || manager[164] || *(int*)(manager + 28) <= 0) return 0;
    definitions = *(unsigned char***)(manager + 16);
    if (!ConsoleCmd_IsReadable(definitions, sizeof(void*)) || !ConsoleCmd_IsReadable(definitions[0], 88)) return 0;
    backend = *(unsigned char**)(definitions[0] + 72);
    if (!ConsoleCmd_IsReadable(backend, 96)) return 0;
    context = *(unsigned char**)(backend + 16);
    if (!ConsoleCmd_IsReadable(context, 280) || *(void**)context != g_base + 0x2B5BE00 || !context[266] || !ConsoleCmd_IsReadable(*(void**)(context + 160), sizeof(void*))) return 0;
    console = *(unsigned char**)(g_base + 0x35E1A80);
    if (!ConsoleCmd_IsReadable(console, 224)) return 0;
    network = *(void**)(console + 144);
    if (!ConsoleCmd_IsReadable(network, sizeof(void*))) return 0;
    table = *(void***)network;
    if (!ConsoleCmd_IsReadable(table, 3 * sizeof(void*)) || !ConsoleCmd_IsReadable(table[2], 1)) return 0;
    return !((Unary)table[2])(network);
}

static int ScopeReady(void* scope) {
    int count;
    if (!ConsoleCmd_IsReadable(scope, 16)) return 0;
    count = *(int*)((unsigned char*)scope + 8);
    return count > 0 && count < 100000 && ConsoleCmd_IsReadable(*(void**)scope, (size_t)count * 16);
}

static int Completed(unsigned char* achievement) {
    return ((Unary)(*(void***)achievement)[12])(achievement) != 0;
}

static int Possible(unsigned char* achievement, void* scope) {
    void* node = *(void**)(achievement + 16);
    int result;
    if (!node) return 1;
    ++g_possible;
    __try { result = ((Eval)(*(void***)node)[3])(node, scope) != 0; }
    __finally { --g_possible; }
    return result;
}

static void Append(unsigned char* manager, int offset, unsigned char* achievement) {
    typedef void* (__fastcall *Add)(void*, const void*);
    ((Add)(g_base + 0x1205A0))(manager + offset, &achievement);
    if (offset == 40) {
        unsigned short id = *(unsigned short*)(achievement + 80);
        ((Add)(g_base + 0x61D0D0))(manager + 136, &id);
    }
}

static void VanillaCandidates(unsigned char* manager, void* scope) {
    int i, count = *(int*)(manager + 28);
    unsigned char** all = *(unsigned char***)(manager + 16);
    if (count < 0 || count > 100000 || !ConsoleCmd_IsReadable(all, (size_t)count * sizeof(void*))) return;
    for (i = 0; i < count; ++i) {
        unsigned char* achievement = all[i];
        if (Completed(achievement)) Append(manager, 64, achievement);
        else Append(manager, Possible(achievement, scope) ? 40 : 88, achievement);
    }
    InterlockedExchange(&g_needRebuild, 0);
    InterlockedIncrement(&g_rebuilds);
    Plugin_Log("[achievement] compatible candidates: pending=%d completed=%d excluded=%d; native possible preserved", *(int*)(manager + 52), *(int*)(manager + 76), *(int*)(manager + 100));
}

static unsigned char __fastcall Eligible(void* manager) {
    return Compatible((unsigned char*)manager) ? 1 : g_eligible(manager);
}

static unsigned char __fastcall Iron(void* node) {
    if (g_possible > 0) {
        InterlockedIncrement(&g_ironOverrides);
        return *((unsigned char*)node + 88) == 1;
    }
    return g_iron(node);
}

static void __fastcall Rebuild(unsigned char* manager, void* scope) {
    int supplement = Compatible(manager) && !NativeGate(manager) && ScopeReady(scope);
    g_rebuild(manager, scope);
    if (supplement) VanillaCandidates(manager, scope);
}

static void __fastcall Restore(unsigned char* manager, void* ids) {
    int i, j, count, saved;
    unsigned char** all;
    unsigned short* values;
    int supplement = Compatible(manager) && !NativeGate(manager);
    g_restore(manager, ids);
    if (!supplement || !ConsoleCmd_IsReadable(ids, 16)) { InterlockedExchange(&g_needRebuild, 1); return; }
    saved = *(int*)((unsigned char*)ids + 12);
    values = *(unsigned short**)ids;
    if (saved <= 0 || saved > 100000 || !ConsoleCmd_IsReadable(values, (size_t)saved * 2)) { InterlockedExchange(&g_needRebuild, 1); return; }
    count = *(int*)(manager + 28); all = *(unsigned char***)(manager + 16);
    if (count < 0 || count > 100000 || !ConsoleCmd_IsReadable(all, (size_t)count * sizeof(void*))) return;
    for (i = 0; i < count; ++i) {
        unsigned char* achievement = all[i];
        if (Completed(achievement)) Append(manager, 64, achievement);
        else {
            unsigned short id = *(unsigned short*)(achievement + 80);
            for (j = 0; j < saved && values[j] != id; ++j) {}
            Append(manager, j < saved ? 40 : 88, achievement);
        }
    }
    InterlockedExchange(&g_needRebuild, 0);
}

static void __fastcall Update(unsigned char* manager, void* scope) {
    int i;
    int supplement = Compatible(manager) && !NativeGate(manager) && ScopeReady(scope);
    if (supplement && g_needRebuild) Rebuild(manager, scope);
    g_update(manager, scope);
    if (!supplement) return;
    InterlockedIncrement(&g_ticks);
    for (i = *(int*)(manager + 52) - 1; i >= 0; --i) {
        unsigned char* achievement = (*(unsigned char***)(manager + 40))[i];
        void* node = *(void**)(achievement + 24);
        if (!Completed(achievement) && (!node || ((Eval)(*(void***)node)[3])(node, scope))) {
            typedef __int64 (__fastcall *Complete)(void*, void*);
            Plugin_Log("[achievement] native happened true, invoking original completion id=%u", *(unsigned short*)(achievement + 80));
            ((Complete)(g_base + 0x61CE50))(manager, achievement);
            InterlockedIncrement(&g_nativeCompletions);
        }
    }
}

void AchievementCompat_DefinitionsLoaded(void) { InterlockedExchange(&g_needRebuild, 1); }
int AchievementCompat_Installed(void) { return g_installed != 0; }

int AchievementCompat_Install(void) {
    IMAGE_DOS_HEADER* dos;
    IMAGE_NT_HEADERS64* nt;
    void* targets[5]; int created = 0, i;
    if (g_installed) return 1;
    g_base = (unsigned char*)GetModuleHandleW(NULL); dos = (IMAGE_DOS_HEADER*)g_base;
    if (!g_base || dos->e_magic != IMAGE_DOS_SIGNATURE || dos->e_lfanew <= 0 || dos->e_lfanew > 4096) return 0;
    nt = (IMAGE_NT_HEADERS64*)(g_base + dos->e_lfanew);
    if (nt->Signature != IMAGE_NT_SIGNATURE || nt->FileHeader.TimeDateStamp != 0x6AA123BB || nt->OptionalHeader.SizeOfImage != 0x37EC000 || !InlineHook_Init()) return 0;
    targets[0] = g_base + 0x6201F0; targets[1] = g_base + 0x3DB5C0; targets[2] = g_base + 0x6202C0; targets[3] = g_base + 0x620570; targets[4] = g_base + 0x621040;
    if (MH_CreateHook(targets[0], Eligible, (void**)&g_eligible) != MH_OK) goto fail; ++created;
    if (MH_CreateHook(targets[1], Iron, (void**)&g_iron) != MH_OK) goto fail; ++created;
    if (MH_CreateHook(targets[2], Rebuild, (void**)&g_rebuild) != MH_OK) goto fail; ++created;
    if (MH_CreateHook(targets[3], Restore, (void**)&g_restore) != MH_OK) goto fail; ++created;
    if (MH_CreateHook(targets[4], Update, (void**)&g_update) != MH_OK) goto fail; ++created;
    for (i = 0; i < 5; ++i) if (MH_QueueEnableHook(targets[i]) != MH_OK) goto fail;
    if (MH_ApplyQueued() != MH_OK) goto fail;
    InterlockedExchange(&g_installed, 1); return 1;
fail:
    for (i = 0; i < created; ++i) { MH_QueueDisableHook(targets[i]); MH_DisableHook(targets[i]); }
    MH_ApplyQueued(); for (i = 0; i < created; ++i) MH_RemoveHook(targets[i]); return 0;
}

static long long __fastcall Status(CmdResult* out, CmdArgs* args) {
    unsigned char* manager;
    char text[768]; (void)args; ConsoleCmd_InitResult(out);
    if (!g_installed) { ConsoleCmd_SetMessage(out, "[error] Achievement compatibility installation unavailable; no state read."); return (long long)out; }
    manager = *(unsigned char**)(g_base + 0x3330460);
    _snprintf_s(text, sizeof(text), _TRUNCATE,
        "[info] Achievement compatibility: installed=%ld active=%d rebuilds=%ld ticks=%ld iron_possible_overrides=%ld native_completions=%ld need_rebuild=%ld. Original happened and platform completion retained; Steam confirmation requires independent verification.",
        g_installed, Compatible(manager), g_rebuilds, g_ticks, g_ironOverrides, g_nativeCompletions, g_needRebuild);
    ConsoleCmd_SetMessage(out, text); out->ok = g_installed != 0; return (long long)out;
}

int AchievementCompat_RegisterCommands(void) {
    CmdDef def = {"achievementcompat", "Read achievement compatibility and native completion counters", "achcompat", 0, {0}, Status};
    return ConsoleCmd_RegisterAll(&def, 1);
}
