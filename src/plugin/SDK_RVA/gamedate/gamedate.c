#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>

#include "carrier.h"
#include "console_cmd.h"
#include "gamedate.h"

extern void Plugin_Log(const char* fmt, ...);

static unsigned char* Img(void)
{
    return (unsigned char*)GetModuleHandleA(NULL);
}

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

int GameDate_SetRaw(int raw)
{
    unsigned char* gs = GameDate_GameState();
    if (gs == NULL) return 0;
    if (!ConsoleCmd_IsReadable(gs + OFF_GD_RAW, 4)) return 0;
    *(int*)(gs + OFF_GD_RAW) = raw;
    return (*(int*)(gs + OFF_GD_RAW) == raw);
}

int GameDate_GetParts(int* year, int* month, int* day)
{
    unsigned char* gs = GameDate_GameState();
    if (gs == NULL) return 0;
    if (!ConsoleCmd_IsReadable(gs + OFF_GD_MONTH0, 4)) return 0;
    if (!ConsoleCmd_IsReadable(gs + OFF_GD_DAY, 4)) return 0;
    if (year != NULL)  *year  = *(int*)(gs + OFF_GD_YEAR);
    if (month != NULL) *month = *(int*)(gs + OFF_GD_MONTH0) + 1;
    if (day != NULL)   *day   = *(int*)(gs + OFF_GD_DAY) + 1;
    return 1;
}

static const int kMonthDays[12] = { 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31 };

#define GD_BASE_HOURS  43800000
#define GD_BASE_DAYS   182500

static int ParseInt(const char** pp)
{
    const char* p = *pp;
    int v = 0;
    int seen = 0;
    if (pp == NULL) return -1;
    while (*p >= '0' && *p <= '9') {
        v = v * 10 + (int)(*p - '0');
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
    int days;
    int raw;
    int i;

    if (!ParseDateText(text, &y, &mo, &d, &h)) return 0;
    if (y < 1 || y > 9999) return 0;
    if (mo < 1 || mo > 12) return 0;
    if (d < 1 || d > kMonthDays[mo - 1]) return 0;
    if (h < 0 || h > 23) return 0;

    days = 365 * (y - 500);
    for (i = 0; i < mo - 1; ++i) days += kMonthDays[i];
    days += (d - 1);
    raw = GD_BASE_HOURS + (GD_BASE_DAYS + days) * 24 + h;
    return GameDate_SetRaw(raw);
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
    char msg[96];

    if (out == NULL) return 0;
    ConsoleCmd_InitResult(out);

    if (!ConsoleCmd_GetArg(args, 0, arg, sizeof(arg))) {
        if (GameDate_GetParts(&y, &mo, &d)) {
            _snprintf_s(msg, sizeof(msg), _TRUNCATE, "Game date is %d.%d.%d", y, mo, d);
            ConsoleCmd_SetMessage(out, msg);
            out->ok = 1;
            Plugin_Log("[gamedate] read only: %d.%d.%d", y, mo, d);
        } else {
            ConsoleCmd_SetMessage(out, "Game date unknown");
            Plugin_Log("[gamedate] gamestate not ready");
        }
        return (long long)out;
    }

    before = GameDate_GetRaw();
    if (!GameDate_SetFromText(arg)) {
        ConsoleCmd_SetMessage(out, "Date not changed");
        Plugin_Log("[gamedate] parse/apply failed for [%s]", arg);
        return (long long)out;
    }
    after = GameDate_GetRaw();
    if (GameDate_GetParts(&y, &mo, &d)) {
        _snprintf_s(msg, sizeof(msg), _TRUNCATE, "Date set %d.%d.%d", y, mo, d);
        ConsoleCmd_SetMessage(out, msg);
    } else {
        ConsoleCmd_SetMessage(out, "Date set");
    }
    out->ok = 1;
    Plugin_Log("[gamedate] arg=[%s]  raw %d -> %d  now %d.%d.%d", arg, before, after, y, mo, d);
    return (long long)out;
}

static const CmdDef kDateCmds[] = {
    { "setgamedate", "Set the in-game date", "sgd", 1, { "<y.m.d.h>" }, &Handler_SetGameDate },
};

int GameDate_RegisterCommands(void)
{
    return ConsoleCmd_RegisterAll(kDateCmds, (int)(sizeof(kDateCmds) / sizeof(kDateCmds[0])));
}
