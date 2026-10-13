#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>

#include "console_cmd.h"
#include "gamedate.h"

#include "../common/plugin_log.h"

static unsigned char* Img(void)
{
    return (unsigned char*)GetModuleHandleA(NULL);
}

static const int kGregorianMonthDayCounts[12] = { 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31 };

#define GD_BASE_HOURS  43800000
#define GD_BASE_DAYS   182500
#define GD_EPOCH_YEAR  500

unsigned char* GameDate_GameState(void)
{
    unsigned char* img = Img();
    if (img == NULL) return NULL;
    if (!ConsoleCmd_IsReadable(img + RVA_GD_GS_GLOBAL, sizeof(void*))) return NULL;
    return *(unsigned char**)(img + RVA_GD_GS_GLOBAL);
}

int GameDate_GetRaw(void)
{
    unsigned char* gs = GameDate_GameState();
    if (gs == NULL) return -1;
    if (!ConsoleCmd_IsReadable(gs + OFF_GD_RAW, 4)) return -1;
    return *(int*)(gs + OFF_GD_RAW);
}

static void GameDate_SyncDerived(unsigned char* gs, int raw)
{
    int y;
    int mo;
    int d;
    int h;
    int doy;

    if (gs == NULL) return;
    if (!ConsoleCmd_IsReadable(gs + OFF_GD_MONTH0, 4)) return;
    if (!GameDate_DecodeRaw(raw, &y, &mo, &d, &h)) return;

    doy = 0;
    {
        int i;
        for (i = 0; i < mo - 1; ++i) doy += kGregorianMonthDayCounts[i];
        doy += d;
    }

    *(int*)(gs + OFF_GD_YEAR)      = y;
    *(int*)(gs + OFF_GD_MONTHDAYS) = kGregorianMonthDayCounts[mo - 1];
    *(int*)(gs + OFF_GD_DAY)       = d;
    *(int*)(gs + OFF_GD_DOY)       = doy;
    *(int*)(gs + OFF_GD_MONTH0)    = mo - 1;
}

int GameDate_SetRaw(int raw)
{
    unsigned char* gs = GameDate_GameState();
    if (gs == NULL) return 0;
    if (!ConsoleCmd_IsReadable(gs + OFF_GD_RAW, 4)) return 0;
    *(int*)(gs + OFF_GD_RAW) = raw;
    GameDate_SyncDerived(gs, raw);
    GameDateUi_Refresh();
    return (*(int*)(gs + OFF_GD_RAW) == raw);
}

int GameDate_DecodeRaw(int raw, int* year, int* month, int* day, int* hour)
{
    long long off;
    long long days;
    int hr;
    int yr;
    int rem;
    int i;

    off = (long long)raw - GD_BASE_HOURS;
    days = off / 24;
    hr = (int)(off % 24);
    if (hr < 0) { hr += 24; --days; }
    yr = (int)(days / 365);
    rem = (int)(days % 365);
    if (rem < 0) { rem += 365; --yr; }

    if (year != NULL)  *year = yr;
    if (hour != NULL)  *hour = hr;
    for (i = 0; i < 12; ++i) {
        if (rem < kGregorianMonthDayCounts[i]) {
            if (month != NULL) *month = i + 1;
            if (day != NULL)   *day = rem + 1;
            return 1;
        }
        rem -= kGregorianMonthDayCounts[i];
    }
    if (month != NULL) *month = 12;
    if (day != NULL)   *day = 31;
    return 1;
}

int GameDate_EncodeParts(int year, int month, int day, int hour)
{
    int days;
    int i;

    days = 365 * (year - GD_EPOCH_YEAR);
    for (i = 0; i < month - 1; ++i) days += kGregorianMonthDayCounts[i];
    days += (day - 1);
    return GD_BASE_HOURS + (GD_BASE_DAYS + days) * 24 + hour;
}

int GameDate_Add(int unit, int delta)
{
    int raw;
    int y;
    int mo;
    int d;
    int h;
    int scale;
    long long target;
    long long months;

    raw = GameDate_GetRaw();
    if (raw < 0) return 0;

    if (unit != GD_UNIT_MONTH) {
        if (unit == GD_UNIT_HOUR) scale = 1;
        else if (unit == GD_UNIT_DAY) scale = 24;
        else if (unit == GD_UNIT_YEAR) scale = 365 * 24;
        else return 0;
        target = (long long)raw + (long long)delta * scale;
        if (target < INT_MIN || target > INT_MAX) return 0;
        return GameDate_SetRaw((int)target);
    }
    GameDate_DecodeRaw(raw, &y, &mo, &d, &h);
    months = (long long)mo - 1 + delta;
    y += (int)(months / 12);
    mo = (int)(months % 12);
    if (mo < 0) { mo += 12; --y; }
    ++mo;
    if (y < 1) y = 1;
    if (y > 9999) y = 9999;
    if (d > kGregorianMonthDayCounts[mo - 1]) d = kGregorianMonthDayCounts[mo - 1];
    if (d < 1) d = 1;
    return GameDate_SetRaw(GameDate_EncodeParts(y, mo, d, h));
}

int GameDate_GetParts(int* year, int* month, int* day)
{
    return GameDate_GetParts4(year, month, day, NULL);
}

int GameDate_GetParts4(int* year, int* month, int* day, int* hour)
{
    int raw = GameDate_GetRaw();
    if (raw < 0) return 0;
    return GameDate_DecodeRaw(raw, year, month, day, hour);
}

static int ParseInt(const char** pp)
{
    const char* p;
    int v = 0;
    int seen = 0;
    if (pp == NULL || *pp == NULL) return -1;
    p = *pp;
    while (*p >= '0' && *p <= '9') {
        int digit = (int)(*p - '0');
        if (v > (INT_MAX - digit) / 10) return -1;
        v = v * 10 + digit;
        ++p;
        seen = 1;
    }
    if (!seen) return -1;
    *pp = p;
    return v;
}

static int ParseDateText(const char* text, int* y, int* mo, int* d, int* h)
{
    const char* p = text;
    int a;
    int b;
    int c;
    int e;

    if (text == NULL) return 0;
    a = ParseInt(&p);
    if (a < 0 || *p != '.') return 0;
    ++p;
    b = ParseInt(&p);
    if (b < 0 || *p != '.') return 0;
    ++p;
    c = ParseInt(&p);
    if (c < 0) return 0;
    e = 0;
    if (*p == '.') {
        ++p;
        e = ParseInt(&p);
        if (e < 0) return 0;
    }
    if (*p != 0) return 0;
    *y = a;
    *mo = b;
    *d = c;
    *h = e;
    return 1;
}

int GameDate_SetFromText(const char* text)
{
    int y;
    int mo;
    int d;
    int h;

    if (!ParseDateText(text, &y, &mo, &d, &h)) return 0;
    if (y < 1 || y > 9999) return 0;
    if (mo < 1 || mo > 12) return 0;
    if (d < 1 || d > kGregorianMonthDayCounts[mo - 1]) return 0;
    if (h < 0 || h > 23) return 0;

    return GameDate_SetRaw(GameDate_EncodeParts(y, mo, d, h));
}

int GameDate_ReadParamText(void* effectInstance, char* dst, int dstn)
{
    unsigned char* p = (unsigned char*)effectInstance;
    unsigned long long sz;
    unsigned long long cap;
    const char* data;
    int i;

    if (p == NULL || dst == NULL || dstn <= 1) return 0;
    if (!ConsoleCmd_IsReadable(p + OFF_GD_PARAMSTR, 8)) return 0;
    sz  = *(unsigned long long*)(p + OFF_GD_PARAMSTR + 0x10);
    cap = *(unsigned long long*)(p + OFF_GD_PARAMSTR + 0x18);
    if (sz == 0 || sz > (unsigned long long)(GD_TEXT_MAX - 1)) return 0;
    if (cap <= 15) {
        data = (const char*)(p + OFF_GD_PARAMSTR);
    } else {
        data = *(const char**)(p + OFF_GD_PARAMSTR);
        if (data == NULL) return 0;
    }
    if (!ConsoleCmd_IsReadable(data, (size_t)sz)) return 0;
    for (i = 0; i < (int)sz && i < dstn - 1; ++i) dst[i] = data[i];
    dst[i] = 0;
    return i;
}

static long long __fastcall Handler_SetGameDate(CmdResult* out, CmdArgs* args)
{
    char arg[64];
    int before;
    int after;
    int y;
    int mo;
    int d;
    int hr;
    char msg[96];

    if (out == NULL) return 0;
    ConsoleCmd_InitResult(out);

    if (!ConsoleCmd_GetArg(args, 0, arg, sizeof(arg))) {
        ConsoleCmd_SetMessage(out,
            "setgamedate Y.M.D[.H]  e.g. setgamedate 1940.1.1  |  setgamedate 1940.1.1.12");
        Plugin_Log("[gamedate] setgamedate called without argument");
        return (long long)out;
    }

    before = GameDate_GetRaw();
    if (!GameDate_SetFromText(arg)) {
        ConsoleCmd_SetMessage(out, "Date not changed");
        Plugin_Log("[gamedate] parse/apply failed for [%s]", arg);
        return (long long)out;
    }
    after = GameDate_GetRaw();
    if (GameDate_GetParts4(&y, &mo, &d, &hr)) {
        _snprintf_s(msg, sizeof(msg), _TRUNCATE, "Date set %d.%d.%d.%d", y, mo, d, hr);
        ConsoleCmd_SetMessage(out, msg);
    } else {
        ConsoleCmd_SetMessage(out, "Date set");
    }
    out->ok = 1;
    Plugin_Log("[gamedate] arg=[%s]  raw %d -> %d  now %d.%d.%d.%d", arg, before, after, y, mo, d, hr);
    return (long long)out;
}

static int ParseSignedInt(const char* s, int* out)
{
    int neg = 0;
    int v = 0;
    int seen = 0;
    const char* p = s;

    if (s == NULL || out == NULL) return 0;
    while (*p == ' ' || *p == '\t') ++p;
    if (*p == '-') { neg = 1; ++p; }
    else if (*p == '+') { ++p; }
    while (*p >= '0' && *p <= '9') {
        v = v * 10 + (int)(*p - '0');
        ++p;
        seen = 1;
        if (v > 100000) return 0;
    }
    if (!seen || *p != 0) return 0;
    *out = neg ? -v : v;
    return 1;
}

static long long __fastcall Handler_AddTime(CmdResult* out, CmdArgs* args, int unit,
                                             const char* label, const char* commandName)
{
    char arg[64];
    int delta;
    int y;
    int mo;
    int d;
    int h;
    int before;
    int after;
    char msg[96];

    if (out == NULL) return 0;
    ConsoleCmd_InitResult(out);

    if (!ConsoleCmd_GetArg(args, 0, arg, sizeof(arg))) {
        _snprintf_s(msg, sizeof(msg), _TRUNCATE, "%s <int>", commandName);
        ConsoleCmd_SetMessage(out, msg);
        Plugin_Log("[gamedate] %s called without argument", label);
        return (long long)out;
    }

    if (!ParseSignedInt(arg, &delta)) {
        ConsoleCmd_SetMessage(out, "Bad number");
        Plugin_Log("[gamedate] %s bad arg [%s]", label, arg);
        return (long long)out;
    }

    before = GameDate_GetRaw();
    if (!GameDate_Add(unit, delta)) {
        ConsoleCmd_SetMessage(out, "Date not changed");
        Plugin_Log("[gamedate] %s add failed delta=%d", label, delta);
        return (long long)out;
    }
    after = GameDate_GetRaw();
    if (GameDate_GetParts4(&y, &mo, &d, &h)) {
        _snprintf_s(msg, sizeof(msg), _TRUNCATE,
                    "%+d ok, now %d.%d.%d.%d", delta, y, mo, d, h);
        ConsoleCmd_SetMessage(out, msg);
    } else {
        ConsoleCmd_SetMessage(out, "Date changed");
    }
    out->ok = 1;
    Plugin_Log("[gamedate] %s delta=%d  raw %d -> %d", label, delta, before, after);
    return (long long)out;
}

static long long __fastcall Handler_AddYears(CmdResult* out, CmdArgs* args)
{
    return Handler_AddTime(out, args, GD_UNIT_YEAR, "add_years", "addtimeforyears");
}

static long long __fastcall Handler_AddMonths(CmdResult* out, CmdArgs* args)
{
    return Handler_AddTime(out, args, GD_UNIT_MONTH, "add_months", "addtimeformonths");
}

static long long __fastcall Handler_AddDays(CmdResult* out, CmdArgs* args)
{
    return Handler_AddTime(out, args, GD_UNIT_DAY, "add_days", "addtimefordays");
}

static long long __fastcall Handler_AddHours(CmdResult* out, CmdArgs* args)
{
    return Handler_AddTime(out, args, GD_UNIT_HOUR, "add_hours", "addtimeforhours");
}
static const CmdDef kDateCmds[] = {
    { "setgamedate", "Set the in-game date", "sgd", 1, { "<y.m.d.h>" }, &Handler_SetGameDate },
    { "addtimeforyears", "Add years to the in-game date", "atfy", 1, { "<n>" }, &Handler_AddYears },
    { "addtimeformonths", "Add months to the in-game date", "atfm", 1, { "<n>" }, &Handler_AddMonths },
    { "addtimefordays", "Add days to the in-game date", "atfd", 1, { "<n>" }, &Handler_AddDays },
    { "addtimeforhours", "Add hours to the in-game date", "atfh", 1, { "<n>" }, &Handler_AddHours },
};

int GameDate_RegisterCommands(void)
{
    return ConsoleCmd_RegisterAll(kDateCmds, (int)(sizeof(kDateCmds) / sizeof(kDateCmds[0])));
}
