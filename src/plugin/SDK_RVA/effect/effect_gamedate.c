#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include "effect_gamedate.h"
#include <string.h>

#include "carrier.h"
#include "console_cmd.h"
#include "gamedate.h"
#include "effect_reg.h"

extern void Plugin_Log(const char* fmt, ...);

static int g_dateEffectExecCount = 0;

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
    ++g_dateEffectExecCount;

    if (!GameDate_ReadParamText(self, text, sizeof(text))) {
        Plugin_Log("[eff] set_game_date #%d: param unreadable", g_dateEffectExecCount);
        return;
    }

    before = GameDate_GetRaw();
    if (!GameDate_SetFromText(text)) {
        Plugin_Log("[eff] set_game_date #%d: apply failed for [%s]", g_dateEffectExecCount, text);
        return;
    }
    after = GameDate_GetRaw();
    y = 0;
    mo = 0;
    d = 0;
    GameDate_GetParts(&y, &mo, &d);
    Plugin_Log("[eff] set_game_date #%d  arg=[%s]  raw %d -> %d  now %d.%d.%d",
               g_dateEffectExecCount, text, before, after, y, mo, d);
}

static void RunAdd(void* self, void* scope, int unit, const char* tag)
{
    int delta;
    int before;
    int after;
    int y;
    int mo;
    int d;
    int h;

    (void)scope;
    Effect_FlushPendingTooltip();
    ++g_dateEffectExecCount;

    delta = (int)Effect_ParamFloat(self, scope);
    before = GameDate_GetRaw();
    if (!GameDate_Add(unit, delta)) {
        Plugin_Log("[eff] %s #%d: add failed delta=%d", tag, g_dateEffectExecCount, delta);
        return;
    }
    after = GameDate_GetRaw();
    y = 0;
    mo = 0;
    d = 0;
    h = 0;
    GameDate_GetParts4(&y, &mo, &d, &h);
    Plugin_Log("[eff] %s #%d  delta=%d  raw %d -> %d  now %d.%d.%d.%d",
               tag, g_dateEffectExecCount, delta, before, after, y, mo, d, h);
}

static void __fastcall ExecAddYears(void* self, void* scope)
{
    RunAdd(self, scope, GD_UNIT_YEAR, "add_time_for_years");
}

static void __fastcall ExecAddMonths(void* self, void* scope)
{
    RunAdd(self, scope, GD_UNIT_MONTH, "add_time_for_months");
}

static void __fastcall ExecAddDays(void* self, void* scope)
{
    RunAdd(self, scope, GD_UNIT_DAY, "add_time_for_days");
}

static void __fastcall ExecAddHours(void* self, void* scope)
{
    RunAdd(self, scope, GD_UNIT_HOUR, "add_time_for_hours");
}
EFF_DEF(setgamedate, "set_game_date", "Sets the in-game date",
        "EFFECT_SET_GAME_DATE", &ExecSetGameDate)

EFF_DEF(addyears, "add_time_for_years", "Adds years to the in-game date",
        "EFFECT_ADD_TIME_FOR_YEARS", &ExecAddYears)

EFF_DEF(addmonths, "add_time_for_months", "Adds months to the in-game date",
        "EFFECT_ADD_TIME_FOR_MONTHS", &ExecAddMonths)

EFF_DEF(adddays, "add_time_for_days", "Adds days to the in-game date",
        "EFFECT_ADD_TIME_FOR_DAYS", &ExecAddDays)

EFF_DEF(addhours, "add_time_for_hours", "Adds hours to the in-game date",
        "EFFECT_ADD_TIME_FOR_HOURS", &ExecAddHours)

static EffectDef* g_dateEffectDefs[] = {
    &setgamedate_def,
    &addyears_def,
    &addmonths_def,
    &adddays_def,
    &addhours_def
};

#define EFF_DATE_COUNT (int)(sizeof(g_dateEffectDefs) / sizeof(g_dateEffectDefs[0]))

int EffectGameDate_Register(void)
{
    int n;
    int i;
    setgamedate_fill();
    addyears_fill();
    addmonths_fill();
    adddays_fill();
    addhours_fill();
    for (i = 0; i < EFF_DATE_COUNT; ++i) g_dateEffectDefs[i]->supportedScopes = Effect_ScopeAny;
    n = Effect_RegistryRegisterAll(g_dateEffectDefs, EFF_DATE_COUNT);
    Plugin_Log("[eff] date effects registered: %d/%d", n, EFF_DATE_COUNT);
    return n;
}
