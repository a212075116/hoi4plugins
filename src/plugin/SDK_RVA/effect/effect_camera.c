#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <string.h>

#include "carrier.h"
#include "console_cmd.h"
#include "camera_height.h"
#include "effect_reg.h"

extern void Plugin_Log(const char* fmt, ...);

typedef void (__fastcall *CamSetHeightFn)(void* cam, float h);

static int g_cameraEffectExecCount = 0;

static float CameraEffect_ReadCurrentHeight(void* cam)
{
    return *(float*)((unsigned char*)cam + OFF_CAM_HEIGHT);
}

static void CameraEffect_WriteHeight(void* cam, float h)
{
    unsigned char* img = (unsigned char*)GetModuleHandleA(NULL);
    if (img == NULL) return;
    ((CamSetHeightFn)(img + RVA_CAM_SETH))(cam, h);
}

static void __fastcall ExecSetCamHeight(void* self, void* scope)
{
    void* cam;

    Effect_FlushPendingTooltip();
    cam = (void*)Camera_GetObject();
    float before;
    float after;
    float want;

    ++g_cameraEffectExecCount;
    if (cam == NULL) {
        Plugin_Log("[eff] set_camera_height #%d: no camera", g_cameraEffectExecCount);
        return;
    }
    want = Effect_ParamFloat(self, scope);
    before = CameraEffect_ReadCurrentHeight(cam);
    CameraEffect_WriteHeight(cam, want);
    after = CameraEffect_ReadCurrentHeight(cam);
    Plugin_Log("[eff] set_camera_height #%d  %.2f -> %.2f (param %.3f)",
               g_cameraEffectExecCount, before, after, want);
}

static void __fastcall ExecAddCamHeight(void* self, void* scope)
{
    void* cam;

    Effect_FlushPendingTooltip();
    cam = (void*)Camera_GetObject();
    float before;
    float after;
    float delta;

    ++g_cameraEffectExecCount;
    if (cam == NULL) {
        Plugin_Log("[eff] add_camera_height #%d: no camera", g_cameraEffectExecCount);
        return;
    }
    delta = Effect_ParamFloat(self, scope);
    before = CameraEffect_ReadCurrentHeight(cam);
    CameraEffect_WriteHeight(cam, before + delta);
    after = CameraEffect_ReadCurrentHeight(cam);
    Plugin_Log("[eff] add_camera_height #%d  %.2f -> %.2f (delta %.3f)",
               g_cameraEffectExecCount, before, after, delta);
}

static void __fastcall ExecSetLowerLimit(void* self, void* scope)
{
    void* cam;
    int lo;
    int hi;
    int want;
    int old;

    Effect_FlushPendingTooltip();
    cam = (void*)Camera_GetObject();
    if (cam == NULL) {
        Plugin_Log("[eff] set_camera_height_lowerlimit: no camera");
        return;
    }
    if (!Camera_GetLimits(cam, &lo, &hi)) {
        Plugin_Log("[eff] set_camera_height_lowerlimit: limits unreadable");
        return;
    }
    want = (int)Effect_ParamFloat(self, scope);
    old = lo;
    {
        int tlo = Camera_TrueLower();
        int thi = Camera_TrueUpper(cam);
        if (want < tlo) want = tlo;
        if (want > thi) want = thi;
    }
    Camera_SetLowerLimit(cam, want);
    Camera_GetLimits(cam, &lo, &hi);
    if (lo > hi) Camera_SetUpperLimit(cam, lo);
    Effect_SetParamFixed(self, (double)lo);
    {
        int moved = 0;
        float now;
        Camera_ApplyLimits(cam, &lo, &hi, &moved);
        now = CameraEffect_ReadCurrentHeight(cam);
        Plugin_Log("[eff] set_camera_height_lowerlimit  want=%d  lo %d -> %d  hi=%d  height=%.2f  moved=%d",
                   want, old, lo, hi, now, moved);
    }
}

static void __fastcall ExecSetUpperLimit(void* self, void* scope)
{
    void* cam;
    int lo;
    int hi;
    int want;
    int old;

    Effect_FlushPendingTooltip();
    cam = (void*)Camera_GetObject();
    if (cam == NULL) {
        Plugin_Log("[eff] set_camera_height_upperlimit: no camera");
        return;
    }
    if (!Camera_GetLimits(cam, &lo, &hi)) {
        Plugin_Log("[eff] set_camera_height_upperlimit: limits unreadable");
        return;
    }
    want = (int)Effect_ParamFloat(self, scope);
    old = hi;
    {
        int tlo = Camera_TrueLower();
        int thi = Camera_TrueUpper(cam);
        if (want > thi) want = thi;
        if (want < tlo) want = tlo;
    }
    Camera_SetUpperLimit(cam, want);
    Camera_GetLimits(cam, &lo, &hi);
    if (hi < lo) Camera_SetLowerLimit(cam, hi);
    Effect_SetParamFixed(self, (double)hi);
    {
        int moved = 0;
        float now;
        Camera_ApplyLimits(cam, &lo, &hi, &moved);
        now = CameraEffect_ReadCurrentHeight(cam);
        Plugin_Log("[eff] set_camera_height_upperlimit  want=%d  hi %d -> %d  lo=%d  height=%.2f  moved=%d",
                   want, old, hi, lo, now, moved);
    }
}

EFF_DEF(setcamheight, "set_camera_height", "Sets the camera height",
        "EFFECT_SET_CAMERA_HEIGHT", &ExecSetCamHeight)

EFF_DEF(setcamlower, "set_camera_height_lowerlimit", "Sets the camera height lower limit",
        "EFFECT_SET_CAMERA_HEIGHT_LOWERLIMIT", &ExecSetLowerLimit)

EFF_DEF(setcamupper, "set_camera_height_upperlimit", "Sets the camera height upper limit",
        "EFFECT_SET_CAMERA_HEIGHT_UPPERLIMIT", &ExecSetUpperLimit)



EFF_DEF(addcamheight, "add_camera_height", "Adds to the camera height",
        "EFFECT_ADD_CAMERA_HEIGHT", &ExecAddCamHeight)

static EffectDef* g_cameraEffectDefs[] = {
    &setcamheight_def,
    &addcamheight_def,
    &setcamlower_def,
    &setcamupper_def
};

#define EFF_CAMERA_COUNT (int)(sizeof(g_cameraEffectDefs) / sizeof(g_cameraEffectDefs[0]))

int EffectCameras_Register(void)
{
    int n;
    setcamheight_fill();
    addcamheight_fill();
    setcamlower_fill();
    setcamupper_fill();
    n = Effect_RegistryRegisterAll(g_cameraEffectDefs, EFF_CAMERA_COUNT);
    Plugin_Log("[eff] camera effects registered: %d/%d", n, EFF_CAMERA_COUNT);
    return n;
}
