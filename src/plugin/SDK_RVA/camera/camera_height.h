#pragma once

#include "console_cmd.h"
#include "../../adapter/native_adapter.h"

#define OFF_CAM_HEIGHT    NativeAdapter_Field(NFL_CAMERA_HEIGHT)
#define OFF_CAM_MINH      NativeAdapter_Field(NFL_CAMERA_MINIMUM)
#define OFF_CAM_MAXH      NativeAdapter_Field(NFL_CAMERA_MAXIMUM)
#define CAM_TRUE_LOWER    35
#define CAM_TRUE_UPPER_FALLBACK 3000u
#define CAM_MIN_SPAN      50
#define CAM_SMOOTH_STEPS  18
#define CAM_SMOOTH_STEP_MS 16

typedef struct {
    void*  base;
    void*  padding;
    int    dummy;
} CameraModule;

unsigned char* Camera_GetObject(void);
int            Camera_RegisterCommands(void);
int            Camera_RegisterReadCommand(void);
int            Camera_SetHeight(void* cam, float want);
int            Camera_GetLimits(void* cam, int* lo, int* hi);
int            Camera_SetLowerLimit(void* cam, int lo);
int            Camera_SetUpperLimit(void* cam, int hi);
int            Camera_SetLowerLimitSmooth(void* cam, int lo);
int            Camera_SetUpperLimitSmooth(void* cam, int hi);
int            Camera_TrueLower(void);
int            Camera_TrueUpper(void* cam);
int            Camera_CaptureTrueUpperLimit(void);
int            Camera_ClampHeightInto(void* cam, int lo, int hi);
int            Camera_EnsureSpanBetweenLimits(void* cam, int* inOutLo, int* inOutHi);
int            Camera_ApplyLimits(void* cam, int* inOutLo, int* inOutHi, int* moved);
