#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <string.h>

#include "carrier.h"
#include "console_cmd.h"
#include "camera_height.h"
#include "effect_reg.h"

extern void Plugin_Log(const char* fmt, ...);

typedef void (__fastcall *CamSetHeightFn)(void* cam, float h);

static int g_execCalls = 0;

static void* CamObj(void)
{
    unsigned char* img = (unsigned char*)GetModuleHandleA(NULL);
    void* idler;
    void* cam;

    if (img == NULL) return NULL;
    if (!ConsoleCmd_IsReadable(img + RVA_CAM_SLOT, sizeof(void*))) return NULL;
    idler = *(void**)(img + RVA_CAM_SLOT);
    if (idler == NULL) return NULL;
    if (!ConsoleCmd_IsReadable((unsigned char*)idler + 0x750, sizeof(void*))) return NULL;
    cam = *(void**)((unsigned char*)idler + 0x750);
    if (cam == NULL) return NULL;
    if (!ConsoleCmd_IsReadable((unsigned char*)cam + 0x69C, 8)) return NULL;
    return cam;
}

static float CamCurrentHeight(void* cam)
{
    return *(float*)((unsigned char*)cam + 0x69C);
}

static void CamApplyHeight(void* cam, float h)
{
    unsigned char* img = (unsigned char*)GetModuleHandleA(NULL);
    if (img == NULL) return;
    ((CamSetHeightFn)(img + RVA_CAM_SETH))(cam, h);
}

static void __fastcall ExecSetCamHeight(void* self, void* scope)
{
    void* cam;

    Effect_FlushPendingTooltip();
    cam = CamObj();
    float before;
    float after;
    float want;

    ++g_execCalls;
    if (cam == NULL) {
        Plugin_Log("[eff] set_camera_height #%d: no camera", g_execCalls);
        return;
    }
    want = Effect_ParamFloat(self, scope);
    before = CamCurrentHeight(cam);
    CamApplyHeight(cam, want);
    after = CamCurrentHeight(cam);
    Plugin_Log("[eff] set_camera_height #%d  %.2f -> %.2f (param %.3f)",
               g_execCalls, before, after, want);
}

static void __fastcall ExecAddCamHeight(void* self, void* scope)
{
    void* cam;

    Effect_FlushPendingTooltip();
    cam = CamObj();
    float before;
    float after;
    float delta;

    ++g_execCalls;
    if (cam == NULL) {
        Plugin_Log("[eff] add_camera_height #%d: no camera", g_execCalls);
        return;
    }
    delta = Effect_ParamFloat(self, scope);
    before = CamCurrentHeight(cam);
    CamApplyHeight(cam, before + delta);
    after = CamCurrentHeight(cam);
    Plugin_Log("[eff] add_camera_height #%d  %.2f -> %.2f (delta %.3f)",
               g_execCalls, before, after, delta);
}

EFF_DEF(setcamheight, "set_camera_height", "Sets the camera height",
        "EFFECT_SET_CAMERA_HEIGHT", &ExecSetCamHeight)

EFF_DEF(addcamheight, "add_camera_height", "Adds to the camera height",
        "EFFECT_ADD_CAMERA_HEIGHT", &ExecAddCamHeight)

static EffectDef* g_effects[] = {
    &setcamheight_def,
    &addcamheight_def
};

int EffectCameras_Register(void)
{
    int n;
    setcamheight_fill();
    addcamheight_fill();
    n = Effect_RegistryRegisterAll(g_effects, 2);
    Plugin_Log("[eff] camera effects registered: %d/2", n);
    return n;
}
