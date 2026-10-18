#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include "achievement_compat.h"
#include "../console/console_cmd.h"
#include "../hook/inline_hook.h"
#include "../hook/inline_hook_batch.h"
#include "MinHook.h"
#include "../../adapter/native_adapter.h"
#define ACH_RVA(symbol) NativeAdapter_Symbol(symbol)
#define ACH_DEFINITIONS NativeAdapter_Field(NFL_ACH_DEFINITIONS)
#define ACH_COUNT NativeAdapter_Field(NFL_ACH_COUNT)
#define ACH_PENDING_LIST NativeAdapter_Field(NFL_ACH_LIST)
#define ACH_PENDING_COUNT NativeAdapter_Field(NFL_ACH_PENDING)
#define ACH_COMPLETED_COUNT NativeAdapter_Field(NFL_ACH_COMPLETED)
#define ACH_EXCLUDED_COUNT NativeAdapter_Field(NFL_ACH_EXCLUDED)
#define ACH_COMPLETED_LIST (ACH_COMPLETED_COUNT - 12)
#define ACH_EXCLUDED_LIST (ACH_EXCLUDED_COUNT - 12)
#define ACH_FLAG_A0 NativeAdapter_Field(NFL_ACH_FLAG_A0)
#define ACH_FLAG_A3 NativeAdapter_Field(NFL_ACH_FLAG_A3)
#define ACH_FLAG_A4 NativeAdapter_Field(NFL_ACH_FLAG_A4)
#define ACH_MANAGER_SPAN (ACH_FLAG_A4 + 4)
#define ACH_BACKEND NativeAdapter_Field(NFL_ACH_BACKEND)
#define ACH_ID NativeAdapter_Field(NFL_ACH_ID)
#define ACH_NODE_STATE NativeAdapter_Field(NFL_ACH_NODE_STATE)
#define ACH_CONTEXT_READY NativeAdapter_Field(NFL_ACH_CONTEXT_READY)
#define ACH_CONSOLE_NETWORK NativeAdapter_Field(NFL_CONSOLE_NETWORK)

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
    return manager[ACH_FLAG_A3] || (manager[ACH_FLAG_A0 + 1] && manager[ACH_FLAG_A0 + 2] && !g_base[ACH_RVA(NSY_ACH_FLAG_DEBUG)] && !g_base[ACH_RVA(NSY_ACH_FLAG_LOG)]);
}

static int Compatible(unsigned char* manager) {
    unsigned char* console;
    unsigned char** definitions;
    unsigned char* backend;
    unsigned char* context;
    void* network;
    void** table;
    if (!g_installed || !ConsoleCmd_IsReadable(manager, ACH_MANAGER_SPAN) || manager[ACH_FLAG_A0] || manager[ACH_FLAG_A3] || manager[ACH_FLAG_A4] || *(int*)(manager + ACH_COUNT) <= 0) return 0;
    definitions = *(unsigned char***)(manager + ACH_DEFINITIONS);
    if (!ConsoleCmd_IsReadable(definitions, sizeof(void*)) || !ConsoleCmd_IsReadable(definitions[0] + ACH_BACKEND, sizeof(void*))) return 0;
    backend = *(unsigned char**)(definitions[0] + ACH_BACKEND);
    if (!ConsoleCmd_IsReadable(backend, 96)) return 0;
    context = *(unsigned char**)(backend + 16);
    if (!ConsoleCmd_IsReadable(context, 280) || *(void**)context != g_base + ACH_RVA(NSY_ACH_CONTEXT_VT) || !context[ACH_CONTEXT_READY] || !ConsoleCmd_IsReadable(*(void**)(context + 160), sizeof(void*))) return 0;
    console = *(unsigned char**)(g_base + ACH_RVA(NSY_CMD_MANAGER));
    if (!ConsoleCmd_IsReadable(console, 224)) return 0;
    network = *(void**)(console + ACH_CONSOLE_NETWORK);
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
    ((Add)(g_base + ACH_RVA(NSY_ACH_VECTOR_PUSH)))(manager + offset, &achievement);
    if (offset == (int)ACH_PENDING_LIST) {
        unsigned short id = *(unsigned short*)(achievement + ACH_ID);
        ((Add)(g_base + ACH_RVA(NSY_ACH_ID_PUSH)))(manager + 136, &id);
    }
}

static void VanillaCandidates(unsigned char* manager, void* scope) {
    int i, count = *(int*)(manager + ACH_COUNT);
    unsigned char** all = *(unsigned char***)(manager + ACH_DEFINITIONS);
    if (count < 0 || count > 100000 || !ConsoleCmd_IsReadable(all, (size_t)count * sizeof(void*))) return;
    for (i = 0; i < count; ++i) {
        unsigned char* achievement = all[i];
        if (Completed(achievement)) Append(manager, (int)ACH_COMPLETED_LIST, achievement);
        else Append(manager, Possible(achievement, scope) ? (int)ACH_PENDING_LIST : (int)ACH_EXCLUDED_LIST, achievement);
    }
    InterlockedExchange(&g_needRebuild, 0);
    InterlockedIncrement(&g_rebuilds);
    Plugin_Log("[achievement] compatible candidates: pending=%d completed=%d excluded=%d; native possible preserved", *(int*)(manager + ACH_PENDING_COUNT), *(int*)(manager + ACH_COMPLETED_COUNT), *(int*)(manager + ACH_EXCLUDED_COUNT));
}

static unsigned char __fastcall Eligible(void* manager) {
    return Compatible((unsigned char*)manager) ? 1 : g_eligible(manager);
}

static unsigned char __fastcall Iron(void* node) {
    if (g_possible > 0) {
        InterlockedIncrement(&g_ironOverrides);
        return *((unsigned char*)node + ACH_NODE_STATE) == 1;
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
    count = *(int*)(manager + ACH_COUNT); all = *(unsigned char***)(manager + ACH_DEFINITIONS);
    if (count < 0 || count > 100000 || !ConsoleCmd_IsReadable(all, (size_t)count * sizeof(void*))) return;
    for (i = 0; i < count; ++i) {
        unsigned char* achievement = all[i];
        if (Completed(achievement)) Append(manager, (int)ACH_COMPLETED_LIST, achievement);
        else {
            unsigned short id = *(unsigned short*)(achievement + ACH_ID);
            for (j = 0; j < saved && values[j] != id; ++j) {}
            Append(manager, j < saved ? (int)ACH_PENDING_LIST : (int)ACH_EXCLUDED_LIST, achievement);
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
    for (i = *(int*)(manager + ACH_PENDING_COUNT) - 1; i >= 0; --i) {
        unsigned char* achievement = (*(unsigned char***)(manager + ACH_PENDING_LIST))[i];
        void* node = *(void**)(achievement + 24);
        if (!Completed(achievement) && (!node || ((Eval)(*(void***)node)[3])(node, scope))) {
            typedef __int64 (__fastcall *Complete)(void*, void*);
            Plugin_Log("[achievement] native happened true, invoking original completion id=%u", *(unsigned short*)(achievement + ACH_ID));
            ((Complete)(g_base + ACH_RVA(NSY_ACH_COMPLETE)))(manager, achievement);
            InterlockedIncrement(&g_nativeCompletions);
        }
    }
}

void AchievementCompat_DefinitionsLoaded(void) { InterlockedExchange(&g_needRebuild, 1); }
int AchievementCompat_Installed(void) { return g_installed != 0; }

int AchievementCompat_Install(void) {
    IMAGE_DOS_HEADER* dos;
    IMAGE_NT_HEADERS64* nt;
    void* targets[5]; int created = 0;
    if (g_installed) return 1;
    g_base = (unsigned char*)GetModuleHandleW(NULL); dos = (IMAGE_DOS_HEADER*)g_base;
    if (!g_base || dos->e_magic != IMAGE_DOS_SIGNATURE || dos->e_lfanew <= 0 || dos->e_lfanew > 4096) return 0;
    nt = (IMAGE_NT_HEADERS64*)(g_base + dos->e_lfanew);
    if (nt->Signature != IMAGE_NT_SIGNATURE || !NativeAdapter_GroupReady(NG_ACHIEVEMENT) || !InlineHook_Init()) return 0;
    targets[0] = g_base + ACH_RVA(NSY_ACH_ELIGIBLE); targets[1] = g_base + ACH_RVA(NSY_ACH_IRON); targets[2] = g_base + ACH_RVA(NSY_ACH_REBUILD); targets[3] = g_base + ACH_RVA(NSY_ACH_RESTORE); targets[4] = g_base + ACH_RVA(NSY_ACH_UPDATE);
    if (MH_CreateHook(targets[0], Eligible, (void**)&g_eligible) != MH_OK) goto fail; ++created;
    if (MH_CreateHook(targets[1], Iron, (void**)&g_iron) != MH_OK) goto fail; ++created;
    if (MH_CreateHook(targets[2], Rebuild, (void**)&g_rebuild) != MH_OK) goto fail; ++created;
    if (MH_CreateHook(targets[3], Restore, (void**)&g_restore) != MH_OK) goto fail; ++created;
    if (MH_CreateHook(targets[4], Update, (void**)&g_update) != MH_OK) goto fail; ++created;
    if (!InlineHook_EnableQueuedBatch(targets, 5)) goto fail;
    InterlockedExchange(&g_installed, 1); return 1;
fail:
    InlineHook_CleanupCreatedBatch(targets, created); return 0;
}

static long long __fastcall Status(CmdResult* out, CmdArgs* args) {
    unsigned char* manager;
    char text[768]; (void)args; ConsoleCmd_InitResult(out);
    if (!g_installed) { ConsoleCmd_SetMessage(out, "[error] Achievement compatibility installation unavailable; no state read."); return (long long)out; }
    manager = *(unsigned char**)(g_base + ACH_RVA(NSY_ACH_MANAGER));
    _snprintf_s(text, sizeof(text), _TRUNCATE,
        "[info] Achievement compatibility: installed=%ld active=%d rebuilds=%ld ticks=%ld iron_possible_overrides=%ld native_completions=%ld need_rebuild=%ld. Original happened and platform completion retained; Steam confirmation requires independent verification.",
        g_installed, Compatible(manager), g_rebuilds, g_ticks, g_ironOverrides, g_nativeCompletions, g_needRebuild);
    ConsoleCmd_SetMessage(out, text); out->ok = g_installed != 0; return (long long)out;
}

int AchievementCompat_RegisterCommands(void) {
    CmdDef def = {"achievementcompat", "Read achievement compatibility and native completion counters", "achcompat", 0, {0}, Status};
    return ConsoleCmd_RegisterAll(&def, 1);
}
