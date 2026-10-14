#include <windows.h>
#include <string.h>

#include "MinHook.h"
#include "inline_hook.h"
#include "carrier.h"

#include "../common/plugin_log.h"

static int g_hookInit = 0;

int InlineHook_Init(void)
{
    MH_STATUS st;

    if (g_hookInit) return 1;
    st = MH_Initialize();
    if (st != MH_OK) {
        Plugin_Log("[hook] MH_Initialize failed: %s", MH_StatusToString(st));
        return 0;
    }
    g_hookInit = 1;
    Plugin_Log("[hook] MinHook initialized");
    return 1;
}

int InlineHook_InstallInto(void* target, void* detour, void** original)
{
    MH_STATUS st;

    if (target == NULL || detour == NULL || original == NULL) return 0;
    if (!InlineHook_Init()) return 0;

    st = MH_CreateHook(target, detour, original);
    if (st != MH_OK) {
        Plugin_Log("[hook] MH_CreateHook(%p) failed: %s", target, MH_StatusToString(st));
        return 0;
    }
    st = MH_EnableHook(target);
    if (st != MH_OK) {
        Plugin_Log("[hook] MH_EnableHook(%p) failed: %s", target, MH_StatusToString(st));
        MH_RemoveHook(target);
        return 0;
    }
    Plugin_Log("[hook] installed at %p, orig=%p", target, *original);
    return 1;
}

void* InlineHook_Install(void* target, void* detour)
{
    void* original = NULL;
    if (!InlineHook_InstallInto(target, detour, &original)) return NULL;
    return original;
}

int InlineHook_Remove(void* target)
{
    MH_STATUS st;

    if (target == NULL) return 0;
    st = MH_DisableHook(target);
    if (st != MH_OK) return 0;
    st = MH_RemoveHook(target);
    return (st == MH_OK);
}
