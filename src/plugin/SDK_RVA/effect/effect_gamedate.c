#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <string.h>

#include "carrier.h"
#include "console_cmd.h"
#include "gamedate.h"
#include "effect_reg.h"

extern void Plugin_Log(const char* fmt, ...);

static int g_execCalls = 0;

static void __fastcall ExecSetGameDate(void* self, void* scope)
{
    char text[GD_TEXT_MAX];
    int before;
    int after;
    int y;
    int mo;
    int d;

    (void)scope;
    Effect_FlushPendingTooltip();
    ++g_execCalls;

    if (!GameDate_ReadParamText(self, text, sizeof(text))) {
        Plugin_Log("[eff] set_game_date #%d: param unreadable", g_execCalls);
        return;
    }

    before = GameDate_GetRaw();
    if (!GameDate_SetFromText(text)) {
        Plugin_Log("[eff] set_game_date #%d: apply failed for [%s]", g_execCalls, text);
        return;
    }
    after = GameDate_GetRaw();
    y = 0;
    mo = 0;
    d = 0;
    GameDate_GetParts(&y, &mo, &d);
    Plugin_Log("[eff] set_game_date #%d  arg=[%s]  raw %d -> %d  now %d.%d.%d",
               g_execCalls, text, before, after, y, mo, d);
}

EFF_DEF(setgamedate, "set_game_date", "Sets the in-game date",
        "EFFECT_SET_GAME_DATE", &ExecSetGameDate)

static EffectDef* g_dateEffects[] = {
    &setgamedate_def
};

#define EFF_DATE_COUNT (int)(sizeof(g_dateEffects) / sizeof(g_dateEffects[0]))

int EffectGameDate_Register(void)
{
    int n;
    setgamedate_fill();
    n = Effect_RegistryRegisterAll(g_dateEffects, EFF_DATE_COUNT);
    Plugin_Log("[eff] date effects registered: %d/%d", n, EFF_DATE_COUNT);
    return n;
}
