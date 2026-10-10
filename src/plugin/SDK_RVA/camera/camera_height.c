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
    if (g_cameraFallbackUpperLimit > 0) return g_cameraFallbackUpperLimit;
    if (Camera_CaptureTrueUpperLimit() != 0) return g_cameraFallbackUpperLimit;
    (void)cam;
    return (int)CAM_TRUE_UPPER_FALLBACK;
}

int Camera_CaptureTrueUpperLimit(void)
{
    void* cam;
    int lo;
    int hi;

    if (g_cameraFallbackUpperLimit > 0) return 1;

    cam = Camera_GetObject();
    if (cam == NULL) return 0;
    if (!Camera_GetLimits(cam, &lo, &hi)) return 0;
    if (hi <= 0) return 0;
    if (hi <= lo + CAM_MIN_SPAN) return 0;

    g_cameraFallbackUpperLimit = hi;
    Plugin_Log("[cam] true upper limit captured: %d (true lower = %d)",
               g_cameraFallbackUpperLimit, CAM_TRUE_LOWER);
    return 1;
}

static volatile long g_nudgeLock = 0;

void Camera_NudgeInputToSyncLiveHeight(void)
{
    INPUT in[2];
    long prev;

    prev = InterlockedExchange(&g_nudgeLock, 1);
    if (prev != 0) return;

    memset(in, 0, sizeof(in));
    in[0].type = INPUT_MOUSE;
    in[0].mi.dx = 1;
    in[0].mi.dy = 0;
    in[0].mi.dwFlags = MOUSEEVENTF_MOVE;
    in[1].type = INPUT_MOUSE;
    in[1].mi.dx = -1;
    in[1].mi.dy = 0;
    in[1].mi.dwFlags = MOUSEEVENTF_MOVE;
    {
        UINT sent = SendInput(2, in, sizeof(INPUT));
        DWORD err = GetLastError();
        HWND fg = GetForegroundWindow();
        DWORD fgPid = 0;
        DWORD myPid = GetCurrentProcessId();
        if (fg != NULL) GetWindowThreadProcessId(fg, &fgPid);
        Plugin_Log("[nudge] SendInput sent=%u/%d sizeofInput=%d err=%lu fgPid=%lu myPid=%lu fgIsMine=%d",
                   sent, 2, (int)sizeof(INPUT), err, fgPid, myPid, (fgPid == myPid));
    }

    InterlockedExchange(&g_nudgeLock, 0);
}

static volatile LONG g_smoothBusy = 0;
static volatile LONG g_smoothKind = 0;
static volatile LONG g_smoothFromBits = 0;
static volatile LONG g_smoothToBits = 0;
static volatile LONG g_smoothWithHeight = 0;
static volatile LONG g_smoothHeightFromBits = 0;
static volatile LONG g_smoothHeightToBits = 0;

static void CameraSmoothApply(unsigned char* cam, int kind, float v)
{
    if (kind == 2) {
        Camera_SetLowerLimit(cam, (int)v);
    } else if (kind == 3) {
        Camera_SetUpperLimit(cam, (int)v);
    } else {
        *(float*)(cam + OFF_CAM_HEIGHT) = v;
    }
}

static float CameraSmoothRead(unsigned char* cam, int kind)
{
    if (kind == 2) return (float)(*(int*)(cam + OFF_CAM_MINH));
    if (kind == 3) return (float)(*(int*)(cam + OFF_CAM_MAXH));
    return *(float*)(cam + OFF_CAM_HEIGHT);
}

static DWORD WINAPI CameraSmoothThreadProc(LPVOID param)
{
    float from;
    float target;
    float step;
    unsigned char* cam;
    int kind;
    int i;

    (void)param;
    kind = (int)g_smoothKind;
    from = *(float*)&g_smoothFromBits;
    target = *(float*)&g_smoothToBits;
    step = (target - from) / (float)CAM_SMOOTH_STEPS;
    Plugin_Log("[smooth] kind=%d from=%.2f to=%.2f step=%.2f withHeight=%d",
               kind, from, target, step, (int)g_smoothWithHeight);

    for (i = 1; i <= CAM_SMOOTH_STEPS; ++i) {
        cam = Camera_GetObject();
        if (cam == NULL) { Plugin_Log("[smooth] camera lost at step %d", i); break; }
        if (g_smoothWithHeight) {
            float hFrom = *(float*)&g_smoothHeightFromBits;
            float hTo = *(float*)&g_smoothHeightToBits;
            float hv = hFrom + (hTo - hFrom) * (float)i / (float)CAM_SMOOTH_STEPS;
            CameraSmoothApply(cam, 1, hv);
        }
        CameraSmoothApply(cam, kind, from + step * (float)i);
        Sleep(CAM_SMOOTH_STEP_MS);
    }

    cam = Camera_GetObject();
    if (cam != NULL) {
        if (g_smoothWithHeight) {
            CameraSmoothApply(cam, 1, *(float*)&g_smoothHeightToBits);
        }
        CameraSmoothApply(cam, kind, target);
        Plugin_Log("[smooth] done kind=%d final=%.2f (readback %.2f) height=%.2f",
                   kind, target, CameraSmoothRead(cam, kind),
                   *(float*)(cam + OFF_CAM_HEIGHT));
    }

    InterlockedExchange(&g_smoothBusy, 0);
    return 0;
}

static int CameraSmoothStart(void* cam, int kind, float target)
{
    HANDLE th;

    if (InterlockedCompareExchange(&g_smoothBusy, 1, 0) != 0) return 0;
    g_smoothKind = kind;
    g_smoothFromBits = *(LONG*)&(float){ CameraSmoothRead((unsigned char*)cam, kind) };
    g_smoothToBits = *(LONG*)&target;
    th = CreateThread(NULL, 0, CameraSmoothThreadProc, NULL, 0, NULL);
    if (th == NULL) {
        InterlockedExchange(&g_smoothBusy, 0);
        return 0;
    }
    CloseHandle(th);
    return 1;
}

int Camera_SetHeightImmediate(void* cam, float want)
{
    if (cam == NULL) return 0;
    if (!ConsoleCmd_IsReadable((unsigned char*)cam + OFF_CAM_HEIGHT, 4)) return 0;
    *(float*)((unsigned char*)cam + OFF_CAM_HEIGHT) = want;
    return 1;
}

int Camera_SetHeight(void* cam, float want)
{
    if (cam == NULL) return 0;
    if (!ConsoleCmd_IsReadable((unsigned char*)cam + OFF_CAM_HEIGHT, 4)) return 0;
    if (CameraSmoothStart(cam, 1, want)) return 1;
    Plugin_Log("[smooth] busy, immediate height %.2f", want);
    *(float*)((unsigned char*)cam + OFF_CAM_HEIGHT) = want;
    return 1;
}

int Camera_SetLowerLimitSmooth(void* cam, int lo)
{
    float hFrom;
    float hTo;

    if (cam == NULL) return 0;
    if (!ConsoleCmd_IsReadable((unsigned char*)cam + OFF_CAM_MINH, 4)) return 0;
    hFrom = *(float*)((unsigned char*)cam + OFF_CAM_HEIGHT);
    hTo = (hFrom < (float)lo) ? (float)lo : hFrom;
    g_smoothWithHeight = 1;
    g_smoothHeightFromBits = *(LONG*)&hFrom;
    g_smoothHeightToBits = *(LONG*)&hTo;
    if (CameraSmoothStart(cam, 2, (float)lo)) return 1;
    Plugin_Log("[smooth] busy, immediate lower %d", lo);
    g_smoothWithHeight = 0;
    Camera_SetLowerLimit(cam, lo);
    return 1;
}

int Camera_SetUpperLimitSmooth(void* cam, int hi)
{
    if (cam == NULL) return 0;
    if (!ConsoleCmd_IsReadable((unsigned char*)cam + OFF_CAM_MAXH, 4)) return 0;
    if (CameraSmoothStart(cam, 3, (float)hi)) return 1;
    Plugin_Log("[smooth] busy, immediate upper %d", hi);
    Camera_SetUpperLimit(cam, hi);
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
        ConsoleCmd_SetMessage(out, "setcamheight <int>");
        Plugin_Log("[setcamheight] called without argument");
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
    if (!ConsoleCmd_IsReadable((unsigned char*)cam + OFF_CAM_HEIGHT_LIVE, 4)) return 0;
    h = *(float*)((unsigned char*)cam + OFF_CAM_HEIGHT_LIVE);
    if (h != h) {
        Camera_SetHeight(cam, (float)lo);
        Plugin_Log("[cam] height was NaN, pulled to lower %d", lo);
        return 1;
    }
    if (h < (float)lo) { Camera_SetHeight(cam, (float)lo); return 1; }
    if (h > (float)hi) { Camera_SetHeight(cam, (float)hi); return 1; }
    return 0;
}

int Camera_EnsureSpanBetweenLimits(void* cam, int* inOutLo, int* inOutHi)
{
    int lo;
    int hi;
    int raised = 0;

    if (!Camera_GetLimits(cam, &lo, &hi)) return 0;
    if (hi - lo < CAM_MIN_SPAN) {
        hi = lo + CAM_MIN_SPAN;
        Camera_SetUpperLimit(cam, hi);
        raised = 1;
        Plugin_Log("[cam] range too narrow (lo=%d hi=%d), upper raised to %d", lo, hi - CAM_MIN_SPAN, hi);
    }
    if (inOutLo != NULL) *inOutLo = lo;
    if (inOutHi != NULL) *inOutHi = hi;
    return raised;
}

int Camera_ApplyLimits(void* cam, int* inOutLo, int* inOutHi, int* moved)
{
    int lo;
    int hi;
    if (moved != NULL) *moved = 0;
    Camera_EnsureSpanBetweenLimits(cam, &lo, &hi);
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
        ConsoleCmd_SetMessage(out, "setcameraheight_lowerlimit <int>");
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
    Camera_SetLowerLimitSmooth(cam, (int)want);
    Camera_GetLimits(cam, &lo, &hi);
    moved = 0;
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
        ConsoleCmd_SetMessage(out, "setcameraheight_upperlimit <int>");
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
    Camera_SetUpperLimitSmooth(cam, (int)want);
    Camera_GetLimits(cam, &lo, &hi);
    moved = 0;
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

static const CmdDef kCameraCommandDefs[] = {
    { "setcamheight", "Set camera height", "sch", 1, { "<height>" }, &Handler_SetCamHeight },
    { "setcameraheight_lowerlimit", "Set camera height lower limit", "schll", 1, { "<value>" }, &Handler_SetLowerLimit },
    { "setcameraheight_upperlimit", "Set camera height upper limit", "schul", 1, { "<value>" }, &Handler_SetUpperLimit },
};

int Camera_RegisterCommands(void)
{
    return ConsoleCmd_RegisterAll(kCameraCommandDefs, (int)(sizeof(kCameraCommandDefs) / sizeof(kCameraCommandDefs[0])));
}
