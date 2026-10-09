#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>

#include "carrier.h"
#include "console_cmd.h"
#include "camera_height.h"

extern void Plugin_Log(const char* fmt, ...);

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

    if (out == NULL) return 0;
    ConsoleCmd_InitResult(out);

    cam = CamObj();
    if (cam == NULL) {
        ConsoleCmd_SetMessage(out, "Currently,Camera Height is unknown");
        Plugin_Log("[setcamheight] no camera object");
        return (long long)out;
    }

    {
        float cur = *(float*)(cam + OFF_CAM_HEIGHT);
        int lo = *(int*)(cam + OFF_CAM_MINH);
        int hi = *(int*)(cam + OFF_CAM_MAXH);

        if (!ConsoleCmd_GetArg(args, 0, arg, sizeof(arg))) {
            char msg[160];
            _snprintf_s(msg, sizeof(msg), _TRUNCATE,
                        "Currently,Camera Height is %.2f", cur);
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

        if (lo > 0 && want < (float)lo) want = (float)lo;
        if (hi > 0 && want > (float)hi) want = (float)hi;

        *(float*)(cam + OFF_CAM_HEIGHT) = want;

        {
            char msg[160];
            _snprintf_s(msg, sizeof(msg), _TRUNCATE,
                        "Currently,Camera Height is %.2f", want);
            ConsoleCmd_SetMessage(out, msg);
            out->ok = 1;
            Plugin_Log("[setcamheight] %.2f -> %.2f (arg=%s range [%d,%d])",
                       cur, want, arg, lo, hi);
        }
    }
    return (long long)out;
}

static const CmdDef kCamCmds[] = {
    { "setcamheight", "Set camera", "<height>", 1, { "<height>" }, &Handler_SetCamHeight },
};

unsigned char* Camera_GetObject(void)
{
    return CamObj();
}

int Camera_RegisterCommands(void)
{
    return ConsoleCmd_RegisterAll(kCamCmds, (int)(sizeof(kCamCmds) / sizeof(kCamCmds[0])));
}
