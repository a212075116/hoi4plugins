#pragma once

#include "console_cmd.h"

#define RVA_GD_GS_GLOBAL   0x332F260u
#define RVA_GD_DATE_PARSE  0x00533D60u
#define OFF_GD_CGAMEDATE   0x460u
#define OFF_GD_RAW         0x468u
#define OFF_GD_YEAR        0x478u
#define OFF_GD_MONTH0      0x488u
#define OFF_GD_DAY         0x480u
#define OFF_GD_MONTHDAYS   0x47Cu
#define OFF_GD_DOY         0x484u
#define OFF_GD_DIRTY       0x4C0u
#define RVA_GD_UI_DATE_UPDATE 0x18A1EE0u
#define OFF_GD_PARAMSTR    0x108u
#define GD_TEXT_MAX        48

#define GD_UNIT_YEAR       0
#define GD_UNIT_MONTH      1
#define GD_UNIT_DAY        2
#define GD_UNIT_HOUR       3

unsigned char* GameDate_GameState(void);
int  GameDate_GetRaw(void);
int  GameDate_SetRaw(int raw);
int  GameDate_GetParts(int* year, int* month, int* day);
int  GameDate_GetParts4(int* year, int* month, int* day, int* hour);
int  GameDate_DecodeRaw(int raw, int* year, int* month, int* day, int* hour);
int  GameDate_EncodeParts(int year, int month, int day, int hour);
int  GameDate_SetFromText(const char* text);
int  GameDate_Add(int unit, int delta);
int  GameDate_ReadParamText(void* effectInstance, char* dst, int dstn);
int  GameDate_RegisterCommands(void);
int  GameDateUi_Init(void);
int  GameDateUi_HasPanel(void);
int  GameDateUi_Refresh(void);