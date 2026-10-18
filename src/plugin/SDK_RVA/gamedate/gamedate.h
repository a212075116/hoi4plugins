#pragma once
#include "../../adapter/native_adapter.h"

#define RVA_GD_GS_GLOBAL   NativeAdapter_Symbol(NSY_GAMESTATE)
#define OFF_GD_RAW         NativeAdapter_Field(NFL_GD_RAW)
#define OFF_GD_YEAR        NativeAdapter_Field(NFL_GD_YEAR)
#define OFF_GD_MONTH0      NativeAdapter_Field(NFL_GD_MONTH0)
#define OFF_GD_DAY         NativeAdapter_Field(NFL_GD_DAY)
#define OFF_GD_MONTHDAYS   NativeAdapter_Field(NFL_GD_MONTH_DAYS)
#define OFF_GD_DOY         NativeAdapter_Field(NFL_GD_DAY_OF_YEAR)
#define RVA_GD_UI_DATE_UPDATE NativeAdapter_Symbol(NSY_DATE_UI_UPDATE)
#define OFF_GD_PARAMSTR    NativeAdapter_Field(NFL_GD_PARAM_TEXT)
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