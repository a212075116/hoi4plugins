#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>

#include "carrier.h"
#include "console_cmd.h"
#include "camera_height.h"

extern void Plugin_Log(const char* fmt, ...);

typedef void (__fastcall *CamSetHeightFn)(void* cam, float height);

int Camera_SetHeight(void* cam, float want)
{
    HMODULE base;
    unsigned char* img;
    unsigned char* fn;

    if (cam == NULL) return 0;
    base = GetModuleHandleA(NULL);
    if (base == NULL) return 0;
    img = (unsigned char*)base;
    if (!ConsoleCmd_IsReadable(img + RVA_CAM_SETH, sizeof(void*))) return 0;
    fn = img + RVA_CAM_SETH;
    ((CamSetHeightFn)fn)(cam, want);
    return 1;
}

static unsigned char* CamObj(void)
{
    HMODULE base = GetModuleHandleA(NULL);
    unsigned char* img;
    unsigned char* obj;
    unsigned char* cam;

    if (base == NULL) return NULL;
    img = (unsigned char*)base;
    if (!ConsoleCmd_IsReadable(img + RVA_CAM_SLOT, sizeof(void*))) return NULL;
    obj = (unsigned char*)(*(void**)(img + RVA_CAM_SLOT));
    if (obj == NULL) return NULL;
    if (!ConsoleCmd_IsReadable(obj + OFF_CAM_OBJ2CAM, sizeof(void*))) return NULL;
    cam = (unsigned char*)(*(void**)(obj + OFF_CAM_OBJ2CAM));
    if (cam == NULL) return NULL;
    if (!ConsoleCmd_IsReadable(cam + OFF_CAM_HEIGHT, 8)) return NULL;
    return cam;
}

static int ParseFloat(const char* s, float* out)
{
    double v = 0.0;
    double frac = 0.1;
    int neg = 0;
    int seen = 0;
    const char* q = s;

    if (s == NULL || out == NULL) return 0;
    while (*q == ' ' || *q == '\t') ++q;
    if (*q == '-') { neg = 1; ++q; }
    else if (*q == '+') { ++q; }
    while (*q >= '0' && *q <= '9') { v = v * 10.0 + (double)(*q - '0'); ++q; seen = 1; }
    if (*q == '.') {
        ++q;
        while (*q >= '0' && *q <= '9') { v += (double)(*q - '0') * frac; frac *= 0.1; ++q; seen = 1; }
    }
    if (!seen) return 0;
    *out = (float)(neg ? -v : v);
    return 1;
}

static long long __fastcall Handler_SetCamHeight(CmdResult* out, CmdArgs* args)
{
    unsigned char* cam;
    char arg[128];
    float want;
    float cur;
    int lo;
    int hi;
    int used;

    if (out == NULL) return 0;
    ConsoleCmd_InitResult(out);

    cam = CamObj();
    if (cam == NULL) {
        ConsoleCmd_SetMessage(out, "Currently,Camera Height is unknown");
        Plugin_Log("[setcamheight] no camera object");
        return (long long)out;
    }

    cur = *(float*)(cam + OFF_CAM_HEIGHT);
    lo = *(int*)(cam + OFF_CAM_MINH);
    hi = *(int*)(cam + OFF_CAM_MAXH);

    if (!ConsoleCmd_GetArg(args, 0, arg, sizeof(arg))) {
        char msg[160];
        _snprintf_s(msg, sizeof(msg), _TRUNCATE, "Currently,Camera Height is %.2f", cur);
        ConsoleCmd_SetMessage(out, msg);
        out->ok = 1;
        Plugin_Log("[setcamheight] no arg, %s (range [%d,%d])", msg, lo, hi);
        return (long long)out;
    }

    if (!ParseFloat(arg, &want)) {
        ConsoleCmd_SetMessage(out, "Currently,Camera Height is unchanged");
        Plugin_Log("[setcamheight] bad number: %s", arg);
        return (long long)out;
    }

    used = Camera_SetHeight(cam, want);
    if (!used) {
        if (lo > 0 && want < (float)lo) want = (float)lo;
        if (hi > 0 && want > (float)hi) want = (float)hi;
        *(float*)(cam + OFF_CAM_HEIGHT) = want;
        Plugin_Log("[setcamheight] setter unavailable, wrote field directly");
        used = 0;
    } else {
        want = *(float*)(cam + OFF_CAM_HEIGHT);
    }

    {
        char msg[160];
        _snprintf_s(msg, sizeof(msg), _TRUNCATE, "Currently,Camera Height is %.2f", want);
        ConsoleCmd_SetMessage(out, msg);
        out->ok = 1;
        Plugin_Log("[setcamheight] %.2f -> %.2f (arg=%s setter=%d range [%d,%d])",
                   cur, want, arg, used, lo, hi);
    }
    return (long long)out;
}

int Camera_GetLimits(void* cam, int* lo, int* hi)
{
    if (cam == NULL || lo == NULL || hi == NULL) return 0;
    if (!ConsoleCmd_IsReadable((unsigned char*)cam + OFF_CAM_MINH, 8)) return 0;
    *lo = *(int*)((unsigned char*)cam + OFF_CAM_MINH);
    *hi = *(int*)((unsigned char*)cam + OFF_CAM_MAXH);
    return 1;
}

int Camera_SetLowerLimit(void* cam, int lo)
{
    if (cam == NULL) return 0;
    if (!ConsoleCmd_IsReadable((unsigned char*)cam + OFF_CAM_MINH, 4)) return 0;
    if (lo < 0) lo = 0;
    *(int*)((unsigned char*)cam + OFF_CAM_MINH) = lo;
    return 1;
}

int Camera_SetUpperLimit(void* cam, int hi)
{
    if (cam == NULL) return 0;
    if (!ConsoleCmd_IsReadable((unsigned char*)cam + OFF_CAM_MAXH, 4)) return 0;
    if (hi < 1) hi = 1;
    *(int*)((unsigned char*)cam + OFF_CAM_MAXH) = hi;
    return 1;
}

static long long __fastcall Handler_SetLowerLimit(CmdResult* out, CmdArgs* args)
{
    unsigned char* cam;
    char arg[128];
    float want;
    int lo;
    int hi;

    if (out == NULL) return 0;
    ConsoleCmd_InitResult(out);
    cam = CamObj();
    if (cam == NULL) {
        ConsoleCmd_SetMessage(out, "Camera lower limit is unknown");
        return (long long)out;
    }
    if (!Camera_GetLimits(cam, &lo, &hi)) {
        ConsoleCmd_SetMessage(out, "Camera lower limit is unreadable");
        return (long long)out;
    }
    if (!ConsoleCmd_GetArg(args, 0, arg, sizeof(arg))) {
        char msg[160];
        _snprintf_s(msg, sizeof(msg), _TRUNCATE, "Currently,Camera Lower Limit is %d", lo);
        ConsoleCmd_SetMessage(out, msg);
        out->ok = 1;
        return (long long)out;
    }
    if (!ParseFloat(arg, &want)) {
        ConsoleCmd_SetMessage(out, "Camera Lower Limit is unchanged");
        return (long long)out;
    }
    Camera_SetLowerLimit(cam, (int)want);
    Camera_GetLimits(cam, &lo, &hi);
    {
        char msg[160];
        _snprintf_s(msg, sizeof(msg), _TRUNCATE, "Currently,Camera Lower Limit is %d", lo);
        ConsoleCmd_SetMessage(out, msg);
        out->ok = 1;
        Plugin_Log("[setcamlower] arg=%s -> lo=%d hi=%d", arg, lo, hi);
    }
    return (long long)out;
}

static long long __fastcall Handler_SetUpperLimit(CmdResult* out, CmdArgs* args)
{
    unsigned char* cam;
    char arg[128];
    float want;
    int lo;
    int hi;

    if (out == NULL) return 0;
    ConsoleCmd_InitResult(out);
    cam = CamObj();
    if (cam == NULL) {
        ConsoleCmd_SetMessage(out, "Camera upper limit is unknown");
        return (long long)out;
    }
    if (!Camera_GetLimits(cam, &lo, &hi)) {
        ConsoleCmd_SetMessage(out, "Camera upper limit is unreadable");
        return (long long)out;
    }
    if (!ConsoleCmd_GetArg(args, 0, arg, sizeof(arg))) {
        char msg[160];
        _snprintf_s(msg, sizeof(msg), _TRUNCATE, "Currently,Camera Upper Limit is %d", hi);
        ConsoleCmd_SetMessage(out, msg);
        out->ok = 1;
        return (long long)out;
    }
    if (!ParseFloat(arg, &want)) {
        ConsoleCmd_SetMessage(out, "Camera Upper Limit is unchanged");
        return (long long)out;
    }
    Camera_SetUpperLimit(cam, (int)want);
    Camera_GetLimits(cam, &lo, &hi);
    {
        char msg[160];
        _snprintf_s(msg, sizeof(msg), _TRUNCATE, "Currently,Camera Upper Limit is %d", hi);
        ConsoleCmd_SetMessage(out, msg);
        out->ok = 1;
        Plugin_Log("[setcamupper] arg=%s -> lo=%d hi=%d", arg, lo, hi);
    }
    return (long long)out;
}

static const CmdDef kCamCmds[] = {
    { "setcamheight", "Set camera height", "sch", 1, { "<height>" }, &Handler_SetCamHeight },
    { "setcameraheight_lowerlimit", "Set camera height lower limit", "schll", 1, { "<value>" }, &Handler_SetLowerLimit },
    { "setcameraheight_upperlimit", "Set camera height upper limit", "schul", 1, { "<value>" }, &Handler_SetUpperLimit },
};

unsigned char* Camera_GetObject(void)
{
    return CamObj();
}

int Camera_RegisterCommands(void)
{
    return ConsoleCmd_RegisterAll(kCamCmds, (int)(sizeof(kCamCmds) / sizeof(kCamCmds[0])));
}
