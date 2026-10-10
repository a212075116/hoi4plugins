#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>

#include "carrier.h"
#include "console_cmd.h"
#include "camera_height.h"

extern void Plugin_Log(const char* fmt, ...);

typedef void (__fastcall *CamSetHeightFn)(void* cam, float height);

static int g_cameraFallbackUpperLimit = 0;

int Camera_TrueLower(void)
{
    return CAM_TRUE_LOWER;
}

int Camera_TrueUpper(void* cam)
{
    int lo;
    int hi;
    if (g_cameraFallbackUpperLimit <= 0) {
        if (cam != NULL && Camera_GetLimits(cam, &lo, &hi) && hi > 0) {
            g_cameraFallbackUpperLimit = hi;
        } else {
            g_cameraFallbackUpperLimit = (int)CAM_TRUE_UPPER_FALLBACK;
        }
        Plugin_Log("[cam] true upper limit captured: %d (true lower = %d)",
                   g_cameraFallbackUpperLimit, CAM_TRUE_LOWER);
    }
    return g_cameraFallbackUpperLimit;
}

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

unsigned char* Camera_GetObject(void)
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

static int Camera_ParseFloatText(const char* s, float* out)
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

    cam = Camera_GetObject();
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

    if (!Camera_ParseFloatText(arg, &want)) {
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

int Camera_ClampHeightInto(void* cam, int lo, int hi)
{
    float h;
    if (cam == NULL) return 0;
    if (!ConsoleCmd_IsReadable((unsigned char*)cam + OFF_CAM_HEIGHT, 4)) return 0;
    h = *(float*)((unsigned char*)cam + OFF_CAM_HEIGHT);
    if (h < (float)lo) { Camera_SetHeight(cam, (float)lo); return 1; }
    if (h > (float)hi) { Camera_SetHeight(cam, (float)hi); return 1; }
    return 0;
}

int Camera_ApplyLimits(void* cam, int* inOutLo, int* inOutHi, int* moved)
{
    int lo;
    int hi;
    if (moved != NULL) *moved = 0;
    if (!Camera_GetLimits(cam, &lo, &hi)) return 0;
    if (inOutLo != NULL) *inOutLo = lo;
    if (inOutHi != NULL) *inOutHi = hi;
    if (Camera_ClampHeightInto(cam, lo, hi)) {
        if (moved != NULL) *moved = 1;
    }
    return 1;
}

static long long __fastcall Handler_SetLowerLimit(CmdResult* out, CmdArgs* args)
{
    unsigned char* cam;
    char arg[128];
    float want;
    int lo;
    int hi;
    int oldLo;
    int moved;

    if (out == NULL) return 0;
    ConsoleCmd_InitResult(out);
    cam = Camera_GetObject();
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
    if (!Camera_ParseFloatText(arg, &want)) {
        ConsoleCmd_SetMessage(out, "Camera Lower Limit is unchanged");
        return (long long)out;
    }
    oldLo = lo;
    {
        int v = (int)want;
        int tlo = Camera_TrueLower();
        int thi = Camera_TrueUpper(cam);
        if (v < tlo) { v = tlo; Plugin_Log("[setcamlower] clamp %d -> true lower %d", (int)want, tlo); }
        if (v > thi) { v = thi; Plugin_Log("[setcamlower] clamp %d -> true upper %d", (int)want, thi); }
        want = (float)v;
    }
    Camera_SetLowerLimit(cam, (int)want);
    Camera_GetLimits(cam, &lo, &hi);
    if (lo > hi) {
        Camera_SetUpperLimit(cam, lo);
        Plugin_Log("[setcamlower] lo(%d) > hi(%d), hi raised to lo", lo, hi);
    }
    moved = 0;
    Camera_ApplyLimits(cam, &lo, &hi, &moved);
    {
        float now = *(float*)(cam + OFF_CAM_HEIGHT);
        char msg[192];
        if (moved) {
            _snprintf_s(msg, sizeof(msg), _TRUNCATE,
                        "Lower Limit is %d, Height pulled to %.2f (range [%d,%d])",
                        lo, now, lo, hi);
        } else {
            _snprintf_s(msg, sizeof(msg), _TRUNCATE,
                        "Currently,Camera Lower Limit is %d (range [%d,%d])", lo, lo, hi);
        }
        ConsoleCmd_SetMessage(out, msg);
        out->ok = 1;
        Plugin_Log("[setcamlower] arg=%s  lo %d -> %d  hi=%d  height=%.2f  moved=%d",
                   arg, oldLo, lo, hi, now, moved);
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
    int oldHi;
    int moved;

    if (out == NULL) return 0;
    ConsoleCmd_InitResult(out);
    cam = Camera_GetObject();
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
    if (!Camera_ParseFloatText(arg, &want)) {
        ConsoleCmd_SetMessage(out, "Camera Upper Limit is unchanged");
        return (long long)out;
    }
    oldHi = hi;
    {
        int v = (int)want;
        int tlo = Camera_TrueLower();
        int thi = Camera_TrueUpper(cam);
        if (v > thi) { v = thi; Plugin_Log("[setcamupper] clamp %d -> true upper %d", (int)want, thi); }
        if (v < tlo) { v = tlo; Plugin_Log("[setcamupper] clamp %d -> true lower %d", (int)want, tlo); }
        want = (float)v;
    }
    Camera_SetUpperLimit(cam, (int)want);
    Camera_GetLimits(cam, &lo, &hi);
    if (hi < lo) {
        Camera_SetLowerLimit(cam, hi);
        Plugin_Log("[setcamupper] hi(%d) < lo(%d), lo lowered to hi", hi, lo);
    }
    moved = 0;
    Camera_ApplyLimits(cam, &lo, &hi, &moved);
    {
        float now = *(float*)(cam + OFF_CAM_HEIGHT);
        char msg[192];
        if (moved) {
            _snprintf_s(msg, sizeof(msg), _TRUNCATE,
                        "Upper Limit is %d, Height pulled to %.2f (range [%d,%d])",
                        hi, now, lo, hi);
        } else {
            _snprintf_s(msg, sizeof(msg), _TRUNCATE,
                        "Currently,Camera Upper Limit is %d (range [%d,%d])", hi, lo, hi);
        }
        ConsoleCmd_SetMessage(out, msg);
        out->ok = 1;
        Plugin_Log("[setcamupper] arg=%s  hi %d -> %d  lo=%d  height=%.2f  moved=%d",
                   arg, oldHi, hi, lo, now, moved);
    }
    return (long long)out;
}

static DWORD WINAPI Camera_DebugCrashThread(LPVOID p)
{
    volatile unsigned int* q = (volatile unsigned int*)0;
    (void)p;
    *q = 1u;
    return 0;
}

static long long __fastcall Handler_CrashMeMain(CmdResult* out, CmdArgs* args)
{
    volatile unsigned int* q = (volatile unsigned int*)0;
    (void)out;
    (void)args;
    Plugin_Log("[crashme_main] about to dereference NULL on the calling thread");
    *q = 1u;
    return 0;
}

static long long __fastcall Handler_CrashMe(CmdResult* out, CmdArgs* args)
{
    HANDLE t;
    (void)out;
    (void)args;
    Plugin_Log("[crashme] spawning a thread that dereferences NULL");
    t = CreateThread(NULL, 0, Camera_DebugCrashThread, NULL, 0, NULL);
    if (t != NULL) CloseHandle(t);
    return 0;
}

static const CmdDef kCameraCommandDefs[] = {
    { "setcamheight", "Set camera height", "sch", 1, { "<height>" }, &Handler_SetCamHeight },
    { "crashme", "Deliberately crash in a worker thread (tests the crash reporter)", "crm", 0, { "" }, &Handler_CrashMe },
    { "crashme_main", "Deliberately crash on the calling thread (tests the crash reporter)", "crmm", 0, { "" }, &Handler_CrashMeMain },
    { "setcameraheight_lowerlimit", "Set camera height lower limit", "schll", 1, { "<value>" }, &Handler_SetLowerLimit },
    { "setcameraheight_upperlimit", "Set camera height upper limit", "schul", 1, { "<value>" }, &Handler_SetUpperLimit },
};

int Camera_RegisterCommands(void)
{
    return ConsoleCmd_RegisterAll(kCameraCommandDefs, (int)(sizeof(kCameraCommandDefs) / sizeof(kCameraCommandDefs[0])));
}
