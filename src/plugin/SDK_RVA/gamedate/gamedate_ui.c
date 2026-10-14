#include <windows.h>

#include "../common/native_memory.h"
#include "gamedate.h"
#include "inline_hook.h"

#include "../common/plugin_log.h"

typedef long long (__fastcall *UiDateUpdateFn)(void* panel, void* unused);

static UiDateUpdateFn g_origUiDate = NULL;
static void* g_uiPanel = NULL;
static int g_uiHooked = 0;
static int g_uiRefreshCalls = 0;

static long long __fastcall Hook_UiDateUpdate(void* panel, void* unused)
{
    if (panel != NULL) {
        if (g_uiPanel != panel) {
            g_uiPanel = panel;
            Plugin_Log("[gamedate] ui panel captured: %p", panel);
        }
    } else {
        g_uiPanel = NULL;
    }
    return g_origUiDate(panel, unused);
}

int GameDateUi_Init(void)
{
    unsigned char* img;
    void* target;

    if (g_uiHooked) return 1;
    img = (unsigned char*)GetModuleHandleA(NULL);
    if (img == NULL) return 0;
    target = (void*)(img + RVA_GD_UI_DATE_UPDATE);
    if (!InlineHook_InstallInto(target, (void*)Hook_UiDateUpdate, (void**)&g_origUiDate)) {
        g_origUiDate = NULL;
        Plugin_Log("[gamedate] ui hook failed");
        return 0;
    }
    g_uiHooked = 1;
    return 1;
}

int GameDateUi_HasPanel(void)
{
    return (g_uiPanel != NULL);
}

int GameDateUi_Refresh(void)
{
    long long r;

    if (g_uiPanel == NULL || g_origUiDate == NULL) return 0;
    if (!NativeMemory_IsReadable(g_uiPanel, 8)) {
        g_uiPanel = NULL;
        Plugin_Log("[gamedate] ui panel gone, dropped");
        return 0;
    }
    r = g_origUiDate(g_uiPanel, NULL);
    ++g_uiRefreshCalls;
    Plugin_Log("[gamedate] ui refresh #%d panel=%p ret=%lld",
               g_uiRefreshCalls, g_uiPanel, r);
    return 1;
}
