#pragma once

#include "console_cmd.h"

#define RVA_CAM_SLOT      0x332F698u
#define OFF_CAM_OBJ2CAM   0x750u
#define OFF_CAM_HEIGHT    0x69Cu
#define OFF_CAM_MINH      0x6D0u
#define OFF_CAM_MAXH      0x6D4u

typedef struct {
    void*  base;
    void*  padding;
    int    dummy;
} CameraModule;

unsigned char* Camera_GetObject(void);
int            Camera_RegisterCommands(void);
