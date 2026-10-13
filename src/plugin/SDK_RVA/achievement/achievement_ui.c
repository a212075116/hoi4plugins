#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <intrin.h>
#include <stdio.h>
#include "achievement_ui.h"
#include "achievement_compat.h"
#include <string.h>
#include "../console/console_cmd.h"
#include "../hook/inline_hook.h"
#include "MinHook.h"

#define ACH_UI_NAME "enabled_achievement_icons"
#define ACH_UI_TEXT "[hoi4plugins]\xEF\xBC\x9A\xE6\x88\x90\xE5\xB0\xB1\xE5\x85\x81\xE8\xAE\xB8\xE8\xA7\xA3\xE9\x94\x81\xEF\xBC\x81"
static unsigned char* g_uiBase;
static __int64 (__fastcall *g_frontUpdate)(void*);
static unsigned char (__fastcall *g_frontTooltip)(void*, void*, CmdString*);
static volatile LONG g_uiInstalled, g_uiUpdates, g_uiTooltips;

static int IsIcon(void* widget) {
    typedef const CmdString* (__fastcall *GetName)(void*);
    void** table;
    const CmdString* name;
    const char* text;
    if (!ConsoleCmd_IsReadable(widget, sizeof(void*))) return 0;
    table = *(void***)widget;
    if (!ConsoleCmd_IsReadable(table, 23 * sizeof(void*)) || !ConsoleCmd_IsReadable(table[21], 1)) return 0;
    name = ((GetName)table[21])(widget);
    if (!ConsoleCmd_IsReadable(name, sizeof(*name)) || name->size != sizeof(ACH_UI_NAME) - 1) return 0;
    text = name->cap > 15 ? name->u.ptr : name->u.buf;
    return ConsoleCmd_IsReadable(text, name->size) && memcmp(text, ACH_UI_NAME, name->size) == 0;
}

static __int64 __fastcall FrontUpdate(void* view) {
    typedef void* (__fastcall *Find)(void*, const CmdString*, unsigned char);
    typedef void (__fastcall *Show)(void*);
    typedef void (__fastcall *Frame)(void*, unsigned int);
    __int64 result = g_frontUpdate(view);
    void* window;
    void* bottom;
    void* icon;
    void** table;
    CmdString name = {{0}, 6, 15};
    if (!ConsoleCmd_IsReadable((unsigned char*)view + 1384, sizeof(void*))) return result;
    window = *(void**)((unsigned char*)view + 1384);
    if (!ConsoleCmd_IsReadable(window, sizeof(void*))) return result;
    table = *(void***)window;
    if (!ConsoleCmd_IsReadable(table, 56 * sizeof(void*)) || !ConsoleCmd_IsReadable(table[55], 1)) return result;
    memcpy(name.u.buf, "bottom", 7);
    bottom = ((Find)table[55])(window, &name, 1);
    if (!ConsoleCmd_IsReadable(bottom, sizeof(void*))) return result;
    table = *(void***)bottom;
    if (!ConsoleCmd_IsReadable(table, 18 * sizeof(void*)) || !ConsoleCmd_IsReadable(table[17], 1)) return result;
    name.u.ptr = ACH_UI_NAME; name.size = sizeof(ACH_UI_NAME) - 1; name.cap = name.size;
    icon = ((Find)table[17])(bottom, &name, 1);
    if (!IsIcon(icon)) return result;
    table = *(void***)icon;
    if (!ConsoleCmd_IsReadable(table[15], 1) || !ConsoleCmd_IsReadable(table[22], 1)) return result;
    ((Show)table[15])(icon);
    ((Frame)table[22])(icon, 1);
    InterlockedIncrement(&g_uiUpdates);
    return result;
}

static unsigned char __fastcall FrontTooltip(void* view, void* widget, CmdString* out) {
    typedef void* (__fastcall *Assign)(void*, const char*, size_t);
    if (!IsIcon(widget) || !out) return g_frontTooltip(view, widget, out);
    ((Assign)(g_uiBase + 0x129CA0))(out, ACH_UI_TEXT, sizeof(ACH_UI_TEXT) - 1);
    InterlockedIncrement(&g_uiTooltips);
    return 1;
}

int AchievementUi_Install(void) {
    IMAGE_DOS_HEADER* dos;
    IMAGE_NT_HEADERS64* nt;
    void* first; void* second;
    int created = 0;
    if (g_uiInstalled) return 1;
    if (!AchievementCompat_Installed()) return 0;
    g_uiBase = (unsigned char*)GetModuleHandleW(NULL); dos = (IMAGE_DOS_HEADER*)g_uiBase;
    if (!g_uiBase || dos->e_magic != IMAGE_DOS_SIGNATURE || dos->e_lfanew <= 0 || dos->e_lfanew > 4096) return 0;
    nt = (IMAGE_NT_HEADERS64*)(g_uiBase + dos->e_lfanew);
    if (nt->Signature != IMAGE_NT_SIGNATURE || nt->FileHeader.TimeDateStamp != 0x6AA123BB || nt->OptionalHeader.SizeOfImage != 0x37EC000 || !InlineHook_Init()) return 0;
    first = g_uiBase + 0x1CDA120; second = g_uiBase + 0x1CD4570;
    if (MH_CreateHook(first, FrontUpdate, (void**)&g_frontUpdate) != MH_OK) return 0;
    created = 1;
    if (MH_CreateHook(second, FrontTooltip, (void**)&g_frontTooltip) != MH_OK) goto fail;
    created = 2;
    if (MH_QueueEnableHook(first) != MH_OK || MH_QueueEnableHook(second) != MH_OK || MH_ApplyQueued() != MH_OK) goto fail;
    g_uiInstalled = 1; return 1;
fail:
    MH_QueueDisableHook(first); MH_DisableHook(first);
    if (created == 2) { MH_QueueDisableHook(second); MH_DisableHook(second); }
    MH_ApplyQueued(); MH_RemoveHook(first); if (created == 2) MH_RemoveHook(second); return 0;
}

static long long __fastcall Status(CmdResult* out, CmdArgs* args) {
    char text[512]; (void)args; ConsoleCmd_InitResult(out);
    _snprintf_s(text, sizeof(text), _TRUNCATE, "[info] Achievement UI: installed=%ld updates=%ld tooltips=%ld icon=enabled_achievement_icons frame=1 tooltip=" ACH_UI_TEXT ". Presentation only; backend eligibility and happened unchanged.", g_uiInstalled, g_uiUpdates, g_uiTooltips);
    ConsoleCmd_SetMessage(out, text); out->ok = g_uiInstalled != 0; return (long long)out;
}

int AchievementUi_RegisterCommands(void) {
    CmdDef def = {"achievementui", "Read achievement frontend icon and tooltip hook state", "achui", 0, {0}, Status};
    return ConsoleCmd_RegisterAll(&def, 1);
}
