#include <windows.h>
#include <string.h>

#include "MinHook.h"
#include "inline_hook.h"
#include "carrier.h"

extern void Plugin_Log(const char* fmt, ...);

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

void* InlineHook_Install(void* target, void* detour)
{
    MH_STATUS st;
    void* orig = NULL;

    if (target == NULL || detour == NULL) return NULL;
    if (!InlineHook_Init()) return NULL;

    st = MH_CreateHook(target, detour, &orig);
    if (st != MH_OK) {
        Plugin_Log("[hook] MH_CreateHook(%p) failed: %s", target, MH_StatusToString(st));
        return NULL;
    }
    st = MH_EnableHook(target);
    if (st != MH_OK) {
        Plugin_Log("[hook] MH_EnableHook(%p) failed: %s", target, MH_StatusToString(st));
        MH_RemoveHook(target);
        return NULL;
    }
    Plugin_Log("[hook] installed at %p, orig=%p", target, orig);
    return orig;
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
